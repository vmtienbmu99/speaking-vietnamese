#!/usr/bin/env python3
"""Generate Vietnamese sample audio (.mp3) for 6 regional voices (VieNeu-TTS-v3-Turbo) and 2 Edge voices.

Supports both GUI mode (default / .exe double-click) and CLI mode (--cli).
"""

from __future__ import annotations

import argparse
import asyncio
import csv
import hashlib
import io
import json
import os
import re
import sys
import threading
import tkinter as tk
from tkinter import filedialog, messagebox, scrolledtext, ttk
import unicodedata
import urllib.request
import xml.etree.ElementTree as ET
import zipfile
from pathlib import Path

import edge_tts
import soundfile as sf

# (voice_id, display_label, provider, provider_voice_code)
VOICES: list[tuple[str, str, str, str]] = [
    ("bac-f", "Miền Bắc · Nữ (Trúc Ly)", "vieneu", "Trúc Ly"),
    ("bac-m", "Miền Bắc · Nam (Hải Đăng)", "vieneu", "Hải Đăng"),
    ("trung-f", "Miền Trung · Nữ (Ngọc Trân)", "vieneu", "Ngọc Trân"),
    ("trung-m", "Miền Trung · Nam (Quang Sơn)", "vieneu", "Quang Sơn"),
    ("nam-f", "Miền Nam · Nữ (Thùy Dung)", "vieneu", "Thùy Dung"),
    ("nam-m", "Miền Nam · Nam (Adam)", "vieneu", "Adam"),
    ("edge-nu", "Chuẩn · Nữ (Edge Hoài My - Online)", "edge", "vi-VN-HoaiMyNeural"),
    ("edge-nam", "Chuẩn · Nam (Edge Nam Minh - Online)", "edge", "vi-VN-NamMinhNeural"),
]
VOICE_MAP = {v[0]: v for v in VOICES}


def default_project_dir() -> Path:
    """Detect the project root containing index.html."""
    if getattr(sys, "frozen", False):
        exe_dir = Path(sys.executable).resolve().parent
        if (exe_dir / "index.html").exists():
            return exe_dir
        if (exe_dir.parent / "index.html").exists():
            return exe_dir.parent
        return exe_dir
    script_root = Path(__file__).resolve().parent.parent
    if (script_root / "index.html").exists():
        return script_root
    return Path.cwd()


def hf_hub_cache_dir() -> Path:
    """Return HuggingFace hub cache directory."""
    hf_home = os.environ.get("HF_HOME")
    if hf_home:
        return Path(hf_home) / "hub"
    return Path.home() / ".cache" / "huggingface" / "hub"


def check_vieneu_installed() -> tuple[bool, str]:
    """Check whether VieNeu-TTS-v3-Turbo ONNX model files are already cached locally."""
    hub = hf_hub_cache_dir()
    backbone = hub / "models--pnnbao-ump--VieNeu-TTS-v3-Turbo"
    codec = hub / "models--OpenMOSS-Team--MOSS-Audio-Tokenizer-Nano-ONNX"
    has_backbone = backbone.exists() and any(backbone.rglob("*.onnx"))
    has_codec = codec.exists() and any(codec.rglob("*.onnx"))
    if has_backbone and has_codec:
        return True, "Đã cài đặt model VieNeu-TTS-v3-Turbo (Sẵn sàng tạo 6 giọng offline)"
    return False, "Chưa tải model VieNeu-TTS-v3-Turbo (Cần tải 1 lần ~350 MB khi chạy lần đầu)"


def normalize_key(text: str) -> str:
    """Normalize a Vietnamese sentence for consistent manifest lookup."""
    nfc = unicodedata.normalize("NFC", text).strip().lower()
    return re.sub(r"\s+", " ", nfc)


def audio_filename(norm_key: str) -> str:
    """Return a deterministic 12-char SHA-1 filename matching index.html's keyOf()."""
    digest = hashlib.sha1(norm_key.encode("utf-8")).hexdigest()[:12]
    return f"{digest}.mp3"


def extract_from_html(html: str) -> tuple[str, list[str]]:
    """Extract SHEET_URL and built-in sentences from index.html."""
    sheet_match = re.search(r"const\s+SHEET_URL\s*=\s*['\"]([^'\"]*)['\"]", html)
    sheet_url = sheet_match.group(1) if sheet_match else ""

    sentences: list[str] = ["Xin chào"]
    packs_match = re.search(r"const\s+PACKS\s*=\s*\{(.*?)\n\s*\};", html, re.DOTALL)
    if packs_match:
        for m in re.finditer(r"\[\s*['\"]([^'\"]+)['\"]\s*,\s*['\"][^'\"]*['\"]\s*,?\s*\]", packs_match.group(1)):
            sentences.append(m.group(1))
    return sheet_url, sentences


def sheet_csv_urls(sheet_url: str) -> list[str]:
    """Build candidate CSV export URLs matching index.html's sheetUrls()."""
    m = re.search(r"/spreadsheets/d/([\w-]+)", sheet_url)
    if not m or re.search(r"/pub\?|output=csv", sheet_url):
        return [sheet_url] if sheet_url else []
    sheet_id = m.group(1)
    gid_m = re.search(r"[#&?]gid=(\d+)", sheet_url)
    gid_param = f"&gid={gid_m.group(1)}" if gid_m else ""
    return [
        f"https://docs.google.com/spreadsheets/d/{sheet_id}/gviz/tq?tqx=out:csv{gid_param}",
        f"https://docs.google.com/spreadsheets/d/{sheet_id}/export?format=csv{gid_param}",
    ]


def fetch_sheet_sentences(sheet_url: str, log=print) -> list[str]:
    """Fetch sentences from the configured Google Sheet CSV."""
    for url in sheet_csv_urls(sheet_url):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=15) as resp:
                if resp.status != 200:
                    continue
                text = resp.read().decode("utf-8", errors="replace")
                if text.lstrip().startswith("<"):
                    continue
                rows = list(csv.reader(io.StringIO(text)))
                return [
                    row[1].strip()
                    for row in rows[1:]
                    if len(row) >= 2 and row[0].strip() and row[1].strip()
                ]
        except Exception as exc:
            log(f"Cảnh báo: không đọc được {url}: {exc}")
    return []


def read_xlsx_sentences(path: Path) -> list[str]:
    """Read column B (cau) from the first worksheet of an .xlsx file using stdlib."""
    ns = "{http://schemas.openxmlformats.org/spreadsheetml/2006/main}"
    with zipfile.ZipFile(path, "r") as zf:
        shared: list[str] = []
        if "xl/sharedStrings.xml" in zf.namelist():
            root = ET.fromstring(zf.read("xl/sharedStrings.xml"))
            for si in root.findall(f"{ns}si"):
                parts = [t.text or "" for t in si.iter(f"{ns}t")]
                shared.append("".join(parts))

        sheet_name = next((n for n in sorted(zf.namelist()) if n.startswith("xl/worksheets/sheet") and n.endswith(".xml")), None)
        if not sheet_name:
            return []
        sroot = ET.fromstring(zf.read(sheet_name))
        out: list[str] = []
        for r_idx, row in enumerate(sroot.findall(f".//{ns}row")):
            if r_idx == 0:
                continue  # skip header row
            cells: dict[str, str] = {}
            for c in row.findall(f"{ns}c"):
                ref = c.attrib.get("r", "")
                col = "".join(ch for ch in ref if ch.isalpha())
                ctype = c.attrib.get("t", "")
                val_el = c.find(f"{ns}v")
                if ctype == "inlineStr":
                    txt = "".join(t.text or "" for t in c.iter(f"{ns}t"))
                elif val_el is not None and val_el.text is not None:
                    txt = shared[int(val_el.text)] if ctype == "s" else val_el.text
                else:
                    txt = ""
                cells[col] = txt.strip()
            if cells.get("A") and cells.get("B"):
                out.append(cells["B"])
        return out


def read_local_spreadsheet(path: Path, log=print) -> list[str]:
    """Read sentences from a local .csv or .xlsx file (columns: chu_de | cau | nghia)."""
    if not path or not path.exists():
        return []
    try:
        if path.suffix.lower() == ".xlsx":
            return read_xlsx_sentences(path)
        text = path.read_text(encoding="utf-8-sig", errors="replace")
        rows = list(csv.reader(io.StringIO(text)))
        return [row[1].strip() for row in rows[1:] if len(row) >= 2 and row[0].strip() and row[1].strip()]
    except Exception as exc:
        log(f"Cảnh báo: không đọc được file {path.name}: {exc}")
        return []


def collect_sentences(project_dir: Path, extra_file: Path | None = None, log=print) -> dict[str, str]:
    """Collect deduplicated sentences from index.html, Google Sheet, and optional Excel/CSV."""
    index_path = project_dir / "index.html"
    if not index_path.exists():
        raise FileNotFoundError(f"Không tìm thấy index.html trong: {project_dir}")

    html = index_path.read_text(encoding="utf-8")
    sheet_url, builtin = extract_from_html(html)
    from_sheet = fetch_sheet_sentences(sheet_url, log=log) if sheet_url else []
    from_file = read_local_spreadsheet(extra_file, log=log) if extra_file else []

    seen: dict[str, str] = {}
    for s in builtin + from_sheet + from_file:
        key = normalize_key(s)
        if key and key not in seen:
            seen[key] = unicodedata.normalize("NFC", s).strip()

    log(f"Tổng cộng {len(seen)} câu (có sẵn={len(builtin)}, Google Sheet={len(from_sheet)}, Excel/CSV={len(from_file)})")
    return seen


def load_vieneu_engine(log=print):
    """Initialize VieNeu-TTS-v3-Turbo engine (auto-downloads ONNX model on first run)."""
    os.environ.setdefault("HF_HUB_DISABLE_SYMLINKS_WARNING", "1")
    from vieneu import Vieneu

    log("Đang nạp mô hình VieNeu-TTS-v3-Turbo (lần đầu sẽ tự tải ~350 MB)...")
    tts = Vieneu(mode="v3turbo")
    log("Đã nạp xong VieNeu-TTS-v3-Turbo!")
    return tts


def synthesize_vieneu_one(tts, text: str, preset_name: str, out_path: Path) -> None:
    """Synthesize a single sentence using VieNeu-TTS-v3-Turbo and save as MP3."""
    voice = tts.get_preset_voice(preset_name)
    audio = tts.infer(text=text, voice=voice)
    sr = getattr(tts, "sample_rate", 48000)
    sf.write(str(out_path), audio, sr, format="MP3")


async def synthesize_edge(text: str, voice_code: str, rate: str, out_path: Path) -> None:
    """Synthesize a single sentence using Edge TTS and save as MP3."""
    comm = edge_tts.Communicate(text, voice=voice_code, rate=rate)
    await comm.save(str(out_path))


def build_manifest(audio_dir: Path, hashes: dict[str, str]) -> dict:
    """Scan existing voice folders in audio/ and build manifest.json."""
    voices_meta = []
    for vid, label, _provider, _code in VOICES:
        vdir = audio_dir / vid
        if vdir.is_dir():
            count = sum(1 for p in vdir.glob("*.mp3") if p.stat().st_size > 0)
            if count > 0:
                voices_meta.append({"id": vid, "label": label, "count": count})
    return {"voices": voices_meta, "hashes": hashes}


async def generate_all_async(
    project_dir: Path,
    voice_ids: list[str],
    extra_file: Path | None = None,
    rate: str = "+0%",
    force: bool = False,
    log=print,
    on_progress=None,
) -> tuple[int, int, int]:
    """Generate audio files for all selected voices and update audio/manifest.json."""
    seen = collect_sentences(project_dir, extra_file=extra_file, log=log)
    hashes = {key: audio_filename(key) for key in seen}
    audio_dir = project_dir / "audio"
    audio_dir.mkdir(parents=True, exist_ok=True)

    total = len(seen) * len(voice_ids)
    done = 0
    generated = 0
    skipped = 0
    errors = 0

    needs_vieneu = any(VOICE_MAP[vid][2] == "vieneu" for vid in voice_ids)
    tts_engine = None

    def write_manifest_now() -> dict:
        m = build_manifest(audio_dir, hashes)
        (audio_dir / "manifest.json").write_text(json.dumps(m, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        return m

    for vid in voice_ids:
        _vid, label, provider, code = VOICE_MAP[vid]
        vdir = audio_dir / vid
        vdir.mkdir(parents=True, exist_ok=True)

        pending = [
            (orig, vdir / hashes[key])
            for key, orig in seen.items()
            if force or not (vdir / hashes[key]).exists() or (vdir / hashes[key]).stat().st_size == 0
        ]
        skip_count = len(seen) - len(pending)
        skipped += skip_count
        done += skip_count
        if on_progress:
            on_progress(done, total)

        if not pending:
            log(f"--- {label}: đã đủ {len(seen)}/{len(seen)} câu (bỏ qua) ---")
            write_manifest_now()
            continue

        log(f"--- Đang tạo giọng: {label} ({len(pending)} câu mới / {skip_count} đã có) ---")

        if provider == "vieneu":
            if tts_engine is None and needs_vieneu:
                tts_engine = await asyncio.to_thread(load_vieneu_engine, log)
            for idx, (orig, out_path) in enumerate(pending, 1):
                try:
                    await asyncio.to_thread(synthesize_vieneu_one, tts_engine, orig, code, out_path)
                    generated += 1
                    if idx % 10 == 0:
                        write_manifest_now()
                except Exception as exc:
                    errors += 1
                    log(f"Lỗi [{vid}] '{orig}': {exc}")
                done += 1
                if on_progress:
                    on_progress(done, total)
        else:
            sem = asyncio.Semaphore(4)

            async def worker(text: str, out_path: Path) -> None:
                async with sem:
                    await synthesize_edge(text, code, rate, out_path)

            tasks = [worker(orig, out_path) for orig, out_path in pending]
            for coro in asyncio.as_completed(tasks):
                try:
                    await coro
                    generated += 1
                except Exception as exc:
                    errors += 1
                    log(f"Lỗi [{vid}]: {exc}")
                done += 1
                if on_progress:
                    on_progress(done, total)

        write_manifest_now()

    manifest = write_manifest_now()
    manifest_path = audio_dir / "manifest.json"
    log(f"Hoàn tất! Tạo mới: {generated}, Bỏ qua (đã có): {skipped}, Lỗi: {errors}")
    log(f"Đã cập nhật {manifest_path} ({len(manifest['voices'])} giọng khả dụng).")
    return generated, skipped, errors


def launch_gui() -> None:
    root = tk.Tk()
    root.title("Tạo Giọng Nói Tiếng Việt - 6 Giọng Bắc Trung Nam (VieNeu-TTS)")
    root.geometry("700x660")
    root.minsize(620, 580)

    proj_dir = default_project_dir()
    dir_var = tk.StringVar(value=str(proj_dir))
    excel_var = tk.StringVar(value="")
    force_var = tk.BooleanVar(value=False)

    frm = ttk.Frame(root)
    frm.pack(fill="both", expand=True, padx=12, pady=10)

    # Model status banner
    status_box = ttk.LabelFrame(frm, text="Trạng thái công cụ tạo giọng (VieNeu-TTS-v3-Turbo)")
    status_box.pack(fill="x", pady=(0, 8))
    status_lbl = ttk.Label(status_box, text="", wraplength=460)
    status_lbl.pack(side="left", padx=8, pady=6, fill="x", expand=True)
    btn_install = ttk.Button(status_box, text="Tải & Cài đặt Model")
    btn_install.pack(side="right", padx=8, pady=6)

    def refresh_model_status() -> bool:
        ok, msg = check_vieneu_installed()
        if ok:
            status_lbl.config(text="✅ " + msg, foreground="#17855a")
            btn_install.config(text="Đã sẵn sàng", state="disabled")
        else:
            status_lbl.config(text="⚠️ " + msg, foreground="#9a5b00")
            btn_install.config(text="Tải & Cài đặt Model", state="normal")
        return ok

    # Project folder
    ttk.Label(frm, text="Thư mục dự án (chứa file index.html):").pack(anchor="w")
    row_dir = ttk.Frame(frm)
    row_dir.pack(fill="x", pady=(2, 8))
    ttk.Entry(row_dir, textvariable=dir_var).pack(side="left", fill="x", expand=True)

    def pick_dir() -> None:
        chosen = filedialog.askdirectory(initialdir=dir_var.get() or str(proj_dir))
        if chosen:
            dir_var.set(chosen)

    ttk.Button(row_dir, text="Chọn thư mục...", command=pick_dir).pack(side="left", padx=(6, 0))

    # Optional local Excel/CSV
    ttk.Label(frm, text="File Excel / CSV bổ sung (tùy chọn, ngoài Google Sheet trong index.html):").pack(anchor="w")
    row_ex = ttk.Frame(frm)
    row_ex.pack(fill="x", pady=(2, 8))
    ttk.Entry(row_ex, textvariable=excel_var).pack(side="left", fill="x", expand=True)

    def pick_excel() -> None:
        chosen = filedialog.askopenfilename(filetypes=[("Excel / CSV", "*.xlsx *.csv"), ("All files", "*.*")])
        if chosen:
            excel_var.set(chosen)

    ttk.Button(row_ex, text="Chọn file...", command=pick_excel).pack(side="left", padx=(6, 0))
    ttk.Button(row_ex, text="Xóa", command=lambda: excel_var.set("")).pack(side="left", padx=(4, 0))

    # Voices selection
    voices_box = ttk.LabelFrame(frm, text="Chọn giọng cần tạo (.mp3)")
    voices_box.pack(fill="x", pady=(0, 8))

    voice_vars: dict[str, tk.BooleanVar] = {}
    grid = ttk.Frame(voices_box)
    grid.pack(fill="x", padx=8, pady=6)
    for idx, (vid, label, provider, _code) in enumerate(VOICES):
        var = tk.BooleanVar(value=(provider == "vieneu"))
        voice_vars[vid] = var
        ttk.Checkbutton(grid, text=label, variable=var).grid(row=idx // 2, column=idx % 2, sticky="w", padx=8, pady=2)

    quick_row = ttk.Frame(voices_box)
    quick_row.pack(fill="x", padx=8, pady=(0, 6))

    def select_group(mode: str) -> None:
        for vid, _label, provider, _code in VOICES:
            if mode == "6":
                voice_vars[vid].set(provider == "vieneu")
            elif mode == "edge":
                voice_vars[vid].set(provider == "edge")
            elif mode == "all":
                voice_vars[vid].set(True)
            else:
                voice_vars[vid].set(False)

    ttk.Button(quick_row, text="6 giọng 3 miền (Offline)", command=lambda: select_group("6")).pack(side="left", padx=(0, 6))
    ttk.Button(quick_row, text="2 giọng Edge (Online)", command=lambda: select_group("edge")).pack(side="left", padx=(0, 6))
    ttk.Button(quick_row, text="Chọn tất cả", command=lambda: select_group("all")).pack(side="left", padx=(0, 6))
    ttk.Button(quick_row, text="Bỏ chọn", command=lambda: select_group("none")).pack(side="left")

    ttk.Checkbutton(frm, text="Tạo lại cả những câu đã có file (.mp3)", variable=force_var).pack(anchor="w", pady=(0, 8))

    prog = ttk.Progressbar(frm, mode="determinate")
    prog.pack(fill="x", pady=(0, 6))

    btn_run = ttk.Button(frm, text="Bắt đầu tạo audio cho các câu chưa có")
    btn_run.pack(fill="x", pady=(0, 8))

    log_box = scrolledtext.ScrolledText(frm, height=11, state="disabled", font=("Consolas", 9))
    log_box.pack(fill="both", expand=True)

    def append_log(msg: str) -> None:
        def _do() -> None:
            log_box.config(state="normal")
            log_box.insert("end", msg + "\n")
            log_box.see("end")
            log_box.config(state="disabled")

        root.after(0, _do)

    def update_prog(done: int, total: int) -> None:
        def _do() -> None:
            prog["maximum"] = max(1, total)
            prog["value"] = done

        root.after(0, _do)

    def on_install_model() -> None:
        btn_install.config(state="disabled")
        btn_run.config(state="disabled")
        append_log("=== Bắt đầu tải & cài đặt model VieNeu-TTS-v3-Turbo ===")

        def worker() -> None:
            try:
                load_vieneu_engine(log=append_log)
                root.after(0, refresh_model_status)
                root.after(0, lambda: messagebox.showinfo("Thành công", "Đã tải xong model VieNeu-TTS-v3-Turbo! Bạn có thể tạo 6 giọng ngay bây giờ."))
            except Exception as exc:
                append_log(f"LỖI tải model: {exc}")
                root.after(0, refresh_model_status)
                root.after(
                    0,
                    lambda: messagebox.showerror(
                        "Không tải được model",
                        f"Lỗi: {exc}\n\nHướng dẫn:\n1. Kiểm tra kết nối Internet (cần tải ~350 MB từ huggingface.co lần đầu).\n2. Đảm bảo ổ C còn trống ít nhất 1 GB.",
                    ),
                )
            finally:
                root.after(0, lambda: btn_run.config(state="normal"))

        threading.Thread(target=worker, daemon=True).start()

    def on_start() -> None:
        pdir = Path(dir_var.get().strip())
        if not (pdir / "index.html").exists():
            messagebox.showerror("Thiếu index.html", f"Không tìm thấy index.html trong:\n{pdir}")
            return
        selected = [vid for vid, v in voice_vars.items() if v.get()]
        if not selected:
            messagebox.showwarning("Chưa chọn giọng", "Vui lòng chọn ít nhất 1 giọng đọc.")
            return

        needs_vieneu = any(VOICE_MAP[vid][2] == "vieneu" for vid in selected)
        installed, _ = check_vieneu_installed()
        if needs_vieneu and not installed:
            go = messagebox.askyesno(
                "Chưa cài đặt model VieNeu-TTS",
                "Máy bạn chưa tải model VieNeu-TTS-v3-Turbo (~350 MB).\n"
                "Phần mềm sẽ tự động tải về 1 lần duy nhất (cần Internet).\n\n"
                "Bạn có muốn tải và tạo audio luôn không?",
            )
            if not go:
                return

        ex_path = Path(excel_var.get().strip()) if excel_var.get().strip() else None
        btn_run.config(state="disabled")
        btn_install.config(state="disabled")
        prog["value"] = 0
        append_log("=== Bắt đầu kiểm tra & tạo audio ===")

        def worker() -> None:
            try:
                gen, skip, err = asyncio.run(
                    generate_all_async(
                        pdir,
                        selected,
                        extra_file=ex_path,
                        rate="+0%",
                        force=force_var.get(),
                        log=append_log,
                        on_progress=update_prog,
                    )
                )
                root.after(0, refresh_model_status)
                root.after(0, lambda: messagebox.showinfo("Hoàn tất", f"Tạo mới: {gen}\nBỏ qua (đã có): {skip}\nLỗi: {err}"))
            except Exception as exc:
                append_log(f"LỖI: {exc}")
                root.after(0, refresh_model_status)
                root.after(0, lambda: messagebox.showerror("Lỗi", str(exc)))
            finally:
                root.after(0, lambda: btn_run.config(state="normal"))

        threading.Thread(target=worker, daemon=True).start()

    btn_install.config(command=on_install_model)
    btn_run.config(command=on_start)
    refresh_model_status()
    root.mainloop()


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate Vietnamese TTS audio files (6 VieNeu + 2 Edge voices).")
    parser.add_argument("--cli", action="store_true", help="Run in CLI mode instead of GUI")
    parser.add_argument("--dir", default=None, help="Project directory containing index.html")
    parser.add_argument("--excel", default=None, help="Optional local .xlsx or .csv file")
    parser.add_argument("--voices", nargs="+", default=["edge-nu"], choices=list(VOICE_MAP.keys()), help="Voice IDs to generate")
    parser.add_argument("--rate", default="+0%", help="Edge TTS speech rate, e.g. -10%% or +0%%")
    parser.add_argument("--force", action="store_true", help="Regenerate existing MP3 files")
    args = parser.parse_args()

    if not args.cli and len(sys.argv) == 1:
        launch_gui()
        return

    pdir = Path(args.dir).resolve() if args.dir else default_project_dir()
    ex = Path(args.excel).resolve() if args.excel else None
    asyncio.run(generate_all_async(pdir, args.voices, extra_file=ex, rate=args.rate, force=args.force))


if __name__ == "__main__":
    main()
