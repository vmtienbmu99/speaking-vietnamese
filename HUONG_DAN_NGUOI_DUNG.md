# Hướng dẫn sử dụng `TaoGiongNoi.exe` & Cập nhật Audio lên Dự án

Tài liệu này dành cho người sử dụng/quản lý nội dung (không cần biết lập trình) để tự tạo giọng đọc tiếng Việt 3 miền (**Bắc – Trung – Nam**) và đưa lên trang web học tiếng Việt.

---

## Phần 1: Chuẩn bị

1. Máy tính chạy **Windows 10 / Windows 11**.
2. Thư mục dự án trên máy (trong đó có file `index.html`, `asr.mjs`, thư mục `models/`, thư mục `audio/`).
3. Đặt file `TaoGiongNoi.exe` vào **cùng thư mục với `index.html`** (hoặc để ở ngoài Desktop cũng được, lát nữa chọn đường dẫn trong phần mềm).
4. **Kết nối Internet** (chỉ bắt buộc ở **lần chạy đầu tiên** để phần mềm tự tải bộ não AI đọc giọng ~350 MB về máy; những lần sau có thể tạo giọng hoàn toàn offline).
5. Ổ đĩa `C:` còn trống ít nhất **1 GB**.

---

## Phần 2: Các bước chạy `TaoGiongNoi.exe`

### Bước 1: Mở phần mềm
- Bấm đúp vào **`TaoGiongNoi.exe`**.
- *(Nếu Windows hiện bảng xanh "Windows protected your PC", bấm **More info** → bấm **Run anyway** để mở bình thường.)*

### Bước 2: Kiểm tra trạng thái bộ đọc giọng
Nhìn khung **Trạng thái công cụ tạo giọng** ở trên cùng:
- Nếu hiện **`⚠️ Chưa tải model VieNeu-TTS-v3-Turbo`**:
  1. Bấm nút **Tải & Cài đặt Model**.
  2. Đợi vài phút để phần mềm tự tải model về máy (không tắt cửa sổ khi đang tải).
  3. Khi hiện thông báo thành công và chuyển sang màu xanh **`✅ Đã cài đặt model`**, bạn đã sẵn sàng.
- Nếu đã hiện **`✅ Đã cài đặt model`** ngay từ đầu → chuyển thẳng sang Bước 3.

### Bước 3: Chọn nguồn câu tiếng Việt
- **Thư mục dự án:** Phần mềm tự điền thư mục chứa `index.html`. Nếu chưa đúng, bấm **Chọn thư mục...** và trỏ tới thư mục dự án.
- Phần mềm sẽ **tự động đọc**:
  1. Các câu có sẵn trong `index.html`.
  2. Toàn bộ câu trong **Google Sheet** đã gắn sẵn trong `index.html`.
- *(Tùy chọn)* Nếu bạn có thêm file **Excel (`.xlsx`)** hoặc **`.csv`** riêng trên máy, bấm **Chọn file...** ở mục *File Excel / CSV bổ sung*.
  > **Lưu ý cấu trúc file Excel/CSV:** Dòng 1 là tiêu đề, 3 cột theo thứ tự: `chu_de | cau | nghia`. Số nên viết bằng chữ (ví dụ `"hai nghìn"`, không viết `"2000"`).

### Bước 4: Chọn giọng và tạo file âm thanh
1. Tick chọn các giọng bạn muốn tạo (mặc định đã tick sẵn **6 giọng Bắc – Trung – Nam**):
   - Miền Bắc: Nữ (`Trúc Ly`), Nam (`Hải Đăng`)
   - Miền Trung: Nữ (`Ngọc Trân`), Nam (`Quang Sơn`)
   - Miền Nam: Nữ (`Thùy Dung`), Nam (`Adam`)
2. Giữ **bỏ tick** ở ô *Tạo lại cả những câu đã có file* (để phần mềm chỉ tạo thêm cho các câu mới, bỏ qua câu cũ cho nhanh).
3. Bấm **Bắt đầu tạo audio cho các câu chưa có** và chờ thanh tiến trình chạy tới 100% (trung bình ~1–2 giây/câu).

---

## Phần 3: Sau khi chạy `.exe` xong — Làm gì để cập nhật Audio lên Web?

Sau khi phần mềm báo **Hoàn tất**, toàn bộ file âm thanh mới đã được lưu sẵn vào đúng vị trí trong thư mục **`audio/`** của dự án:
- Các file `.mp3` nằm trong thư mục con theo từng giọng (ví dụ `audio/bac-nu/`, `audio/nam-nam/`...).
- File danh sách **`audio/manifest.json`** đã tự động được cập nhật.

Để người học trên web nghe được các giọng mới này, bạn làm theo **1 trong 2 cách** dưới đây:

### Cách A: Cập nhật lên trang web Online (GitHub Pages)

> **Lưu ý quan trọng:** File `TaoGiongNoi.exe` nặng hơn 100 MB nên **không được đẩy lên GitHub** (đã được chặn tự động trong `.gitignore`). Bạn chỉ đẩy thư mục **`audio/`** (và `index.html` nếu có sửa).

#### Nếu bạn dùng GitHub Desktop (khuyên dùng, không cần gõ lệnh):
1. Mở **GitHub Desktop** và chọn repository `speaking-vietnamese`.
2. Ở cột trái sẽ hiện danh sách các file mới trong `audio/` và `audio/manifest.json`.
3. Nhập tên lần cập nhật ở ô **Summary** (ví dụ: `Cap nhat audio moi`) → bấm **Commit to main**.
4. Bấm **Push origin** ở góc trên để đẩy lên GitHub.
5. Đợi khoảng **1–2 phút** cho GitHub Pages cập nhật xong, rồi mở link web và bấm **`Ctrl + F5`** (tải lại trang) để kiểm tra.

#### Nếu bạn dùng dòng lệnh (Terminal / PowerShell):
Mở terminal tại thư mục dự án và chạy lần lượt 3 lệnh:
```powershell
git add audio/
git commit -m "Cap nhat audio giong doc"
git push
```
Sau đó đợi 1–2 phút và mở link web bấm **`Ctrl + F5`**.

### Cách B: Chỉ kiểm tra trực tiếp trên máy tính (`localhost`)
1. Mở terminal tại thư mục dự án, chạy:
   ```powershell
   python scripts/serve.py
   ```
2. Mở trình duyệt tại `http://localhost:8000` và bấm **`Ctrl + F5`**.
3. Chọn giọng ở mục **Giọng mẫu / Voice** trên thanh công cụ và bấm **🔊 Nghe mẫu / Listen** để kiểm tra.

---

## Phần 4: Các lỗi thường gặp & Cách xử lý

| Hiện tượng | Nguyên nhân | Cách khắc phục |
| :--- | :--- | :--- |
| Đã chạy `.exe` xong nhưng lên web vẫn không thấy giọng mới trong danh sách | Chưa đẩy file `audio/manifest.json` lên GitHub hoặc trình duyệt lưu cache cũ | Kiểm tra đã push cả `audio/manifest.json` chưa, sau đó bấm **`Ctrl + F5`** trên trình duyệt |
| Phần mềm không đọc được câu mới từ Google Sheet | Google Sheet chưa mở quyền xem công khai | Vào Google Sheet → **Chia sẻ** → chọn **Bất kỳ ai có đường liên kết** → quyền **Người xem** |
| Bấm *Tải & Cài đặt Model* bị báo lỗi | Mất mạng hoặc ổ C đầy | Kiểm tra Internet, đảm bảo ổ C trống ≥ 1 GB rồi bấm tải lại |
| Không đẩy được code lên GitHub (báo lỗi file > 100 MB) | Đẩy nhầm file `TaoGiongNoi.exe` | Chỉ push thư mục `audio/` (hoặc dùng `git add audio/`), giữ `TaoGiongNoi.exe` ở máy cá nhân |
