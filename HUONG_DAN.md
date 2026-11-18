# Hướng dẫn sử dụng & cập nhật dự án "Nói để nhảy · Speak to Jump"

## 1. Cấu trúc dự án

- `index.html`: Giao diện game, logic chấm điểm từng từ, kết nối Google Sheet và chọn giọng đọc mẫu.
- `asr.mjs`: Bộ nhận dạng giọng nói tiếng Việt chạy cục bộ trên trình duyệt (`onnxruntime-web`).
- `models/vi/`: Các file mô hình AI nhận giọng nói (`Zipformer-30M-RNNT-6000h`).
- `audio/`: Thư mục chứa file âm thanh `.mp3` đọc mẫu theo từng giọng và file `audio/manifest.json` để web tự nhận biết các giọng đang có.
  - `audio/bac-nu/`, `audio/bac-nam/`: Giọng Miền Bắc (Trúc Ly / Hải Đăng)
  - `audio/trung-nu/`, `audio/trung-nam/`: Giọng Miền Trung (Ngọc Trân / Quang Sơn)
  - `audio/nam-nu/`, `audio/nam-nam/`: Giọng Miền Nam (Thùy Dung / Adam)
  - `audio/edge-nu/`, `audio/edge-nam/`: Giọng chuẩn Edge TTS (Hoài My / Nam Minh)
- `TaoGiongNoi.exe`: Công cụ chạy trực tiếp trên Windows (không cần cài Python hay API Token) để kiểm tra cài đặt model và tạo file `.mp3` cho đủ 6 giọng Bắc – Trung – Nam.
- `scripts/generate_audio.py`: Mã nguồn Python của `TaoGiongNoi.exe`.

---

## 2. Cách chạy & đưa lên mạng (Online)

### A. Chạy thử trên máy tính (`localhost`)
Trình duyệt yêu cầu `http://localhost` hoặc `https://` để cấp quyền micro và tải mô hình AI. Mở terminal tại thư mục dự án và chạy:

```powershell
python scripts/serve.py
```
Sau đó mở trình duyệt tại `http://localhost:8000`.

### B. Đưa lên mạng miễn phí bằng GitHub Pages
1. Đẩy toàn bộ code (bao gồm cả thư mục `audio/`) lên repository GitHub.
2. Vào **Settings** → **Pages** → **Build and deployment**:
   - **Source**: `Deploy from a branch`
   - **Branch**: `main` (thư mục `/ (root)`) → bấm **Save**.
3. Đợi ~1–2 phút, truy cập link `https://<ten-tai-khoan>.github.io/<ten-repo>/`.

---

## 3. Cách cập nhật nội dung câu học

Bạn có thể thêm/sửa câu theo 1 trong 3 cách:
1. **Google Sheet (khuyên dùng):**
   - Mở Sheet đã gắn ở biến `SHEET_URL` trong `index.html`.
   - Đảm bảo Sheet để chế độ **Chia sẻ > Bất kỳ ai có đường liên kết > Người xem**.
   - Giữ nguyên dòng 1 là tiêu đề: `chu_de | cau | nghia`.
   - Lưu ý: viết số bằng chữ (ví dụ `"hai nghìn"`, không viết `"2000"`).
2. **File Excel (`.xlsx`) hoặc `.csv` trên máy:** Dùng định dạng 3 cột giống Google Sheet (`chu_de | cau | nghia`) và chọn trực tiếp trong `TaoGiongNoi.exe`.
3. **Sửa trực tiếp trong `index.html`:** Chỉnh sửa mảng `PACKS` hoặc thay link ở `SHEET_URL`.

---

## 4. Cách tạo đủ 6 giọng Bắc – Trung – Nam bằng `TaoGiongNoi.exe`

Công cụ dùng **`VieNeu-TTS-v3-Turbo`** (chạy offline trên máy, **100% miễn phí, không cần API Token, không cần cài `eSpeak NG`**):

1. Đặt `TaoGiongNoi.exe` trong thư mục dự án (cùng cấp với `index.html`) và **bấm đúp để mở**.
2. **Kiểm tra trạng thái model ở khung trên cùng:**
   - Nếu máy **chưa có model**, phần mềm sẽ báo `⚠️ Chưa tải model VieNeu-TTS-v3-Turbo`. Bạn chỉ cần bấm **Tải & Cài đặt Model** (cần Internet lần đầu để tải ~350 MB về máy; những lần sau chạy offline hoàn toàn).
   - Nếu máy **đã có model**, phần mềm sẽ báo `✅ Đã cài đặt model VieNeu-TTS-v3-Turbo`.
3. Kiểm tra **Thư mục dự án** (đã trỏ vào thư mục chứa `index.html`) và chọn thêm **File Excel / CSV bổ sung** nếu có.
4. Chọn các giọng muốn tạo (mặc định đã chọn sẵn **6 giọng 3 miền**; có thể chọn thêm 2 giọng Edge TTS nếu muốn).
5. Bấm **Bắt đầu tạo audio cho các câu chưa có**:
   - Các câu đã có file `.mp3` từ trước sẽ được **bỏ qua tự động**, chỉ tạo mới những câu vừa thêm trong Google Sheet / Excel.
   - Sau khi chạy xong, `audio/manifest.json` tự động cập nhật.
6. Đẩy thư mục `audio/` lên GitHub để web tự hiển thị đủ các giọng mới trong mục **Giọng mẫu / Voice**.

---

## 5. Dành cho lập trình viên: Chạy bằng Python hoặc build lại `.exe`

```powershell
# Cài thư viện cần thiết (chỉ 1 lần)
pip install edge-tts pyinstaller
pip install vieneu --extra-index-url https://pnnbao97.github.io/llama-cpp-python-v0.3.16/cpu/

# Chạy giao diện từ Python
python scripts/generate_audio.py

# Hoặc chạy dòng lệnh (CLI)
python scripts/generate_audio.py --cli --voices bac-nu bac-nam trung-nu trung-nam nam-nu nam-nam

# Build lại file TaoGiongNoi.exe
python -m PyInstaller --onefile --windowed --name TaoGiongNoi --distpath . --workpath build_tmp --specpath build_tmp --collect-all vieneu --collect-all vieneu_utils --collect-all sea_g2p --collect-all soundfile --collect-all onnxruntime --exclude-module gradio --exclude-module fastapi --exclude-module uvicorn --exclude-module matplotlib --exclude-module librosa --exclude-module sklearn --exclude-module pandas scripts/generate_audio.py
```
