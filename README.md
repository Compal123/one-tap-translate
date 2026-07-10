# Dịch Màn Hình

Bong bóng nổi trên màn hình Windows — bật một cái là **toàn bộ chữ trên màn hình được dịch sang tiếng Việt**, đè lên đúng vị trí chữ gốc, chuột bấm xuyên qua, dùng app bên dưới bình thường. Hoạt động với mọi ứng dụng: trình duyệt, PDF dạng ảnh, game, phần mềm máy móc...

Giống tính năng "luôn dịch" của Chrome, nhưng cho **cả màn hình** chứ không riêng trang web.

## Cài đặt

Yêu cầu: Windows 10/11, Python 3.10+.

```
git clone https://github.com/Compal123/dich-man-hinh.git
cd dich-man-hinh
python -m venv .venv
.venv\Scripts\pip install -r requirements.txt
```

## Cách chạy

Nhấp đúp vào `run.bat` (hoặc chạy `.venv\Scripts\python.exe main.py` để xem log lỗi).

## Cách dùng

- **Nhấn bong bóng** → BẬT/TẮT chế độ **dịch sống**: bong bóng chuyển xanh lá "ON",
  màn hình được quét liên tục, bản dịch đè lên chữ gốc, chuột bấm xuyên qua —
  cứ dùng app bên dưới bình thường.
- **Chuột phải → "Dịch một lần"** → chế độ cũ: chụp - dịch - nhấn chuột/Esc để đóng.
- **Kéo bong bóng** để di chuyển; **chuột phải → Thoát** để tắt app.
- Chữ đã dịch được nhớ lại (cache) nên hiện lại tức thì, không tốn mạng;
  màn hình không thay đổi thì app không quét lại.

## Ghi chú kỹ thuật

- OCR: RapidOCR (PaddleOCR bản ONNX) — chạy offline trên máy, đọc được Anh/Trung/Việt và nhiều ngôn ngữ khác, không phụ thuộc gói OCR của Windows.
- Dịch: Google Translate (web) qua thư viện `deep-translator` — cần mạng, miễn phí, phù hợp bản thử nghiệm. Bản sau có thể thay bằng LLM để dịch hiểu ngữ cảnh.
- Mới hỗ trợ màn hình chính (primary monitor).
- Lần nhấn đầu tiên hơi chậm vì phải nạp model OCR.

- Chờ màn hình **đứng yên** mới dịch (đang cuộn trang thì chỉ xóa bản dịch cũ,
  không tốn công dịch cảnh lướt qua).
- Bộ nhớ dịch lưu ở `bo-nho-dich.json` — tắt app vẫn nhớ, dùng càng lâu càng nhanh.
- Tùy chỉnh trong `cai-dat.json` (chuột phải bong bóng → "Mở file cài đặt",
  sửa xong khởi động lại app): ngôn ngữ đích, chu kỳ quét, độ nhạy thay đổi màn hình.

## Hướng phát triển (đóng góp/ý tưởng đều hoan nghênh)

1. Chỉ quét vùng màn hình thay đổi thay vì cả màn hình (giảm trễ OCR).
2. Tùy chọn dịch offline bằng model trên máy (bỏ phụ thuộc mạng).
3. Nút "dịch kỹ bằng AI" cho đoạn văn quan trọng (LLM, hiểu ngữ cảnh/thuật ngữ).
4. Hỗ trợ nhiều màn hình.
5. Bản Android (bong bóng + MediaProjection).
