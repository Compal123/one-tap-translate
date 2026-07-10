# Dịch Màn Hình

🇬🇧 [English version here](README.md)

Bong bóng nổi trên Windows dịch **toàn bộ chữ trên màn hình** — bản dịch đè lên đúng vị trí chữ gốc. Hoạt động với mọi ứng dụng: trình duyệt, PDF dạng ảnh, game, phần mềm máy móc/HMI, phụ đề video...

Giống tính năng "luôn dịch" của Chrome, nhưng cho **cả màn hình** chứ không riêng trang web.

## Vì sao có app này?

Người viết chỉ biết tiếng Việt. Chrome dịch được trang web, nhưng không gì dịch được phần còn lại của màn hình — app desktop, màn hình HMI máy móc, PDF dạng ảnh. OCR có sẵn của Windows thậm chí không hỗ trợ tiếng Việt. App này lấp khoảng trống đó, và dịch được sang mọi ngôn ngữ Google Translate hỗ trợ.

## Tính năng

- **Dịch sống** — quét màn hình liên tục, bản dịch đè tại chỗ, chuột **bấm xuyên qua** lớp dịch nên bạn dùng app bên dưới bình thường. Chờ màn hình đứng yên mới dịch (không tốn công dịch cảnh đang cuộn).
- **Dịch một lần** — nhấn bong bóng, xem ảnh chụp đã dịch, nhấn để đóng.
- **Dịch vùng chọn** — kéo khoanh một vùng, chỉ dịch vùng đó.
- **Bộ nhớ dịch** — mọi câu đã dịch được lưu xuống đĩa (`bo-nho-dich.json`). Chữ từng gặp hiện tức thì, không cần mạng, vĩnh viễn. Dùng càng lâu càng nhanh.
- **Cửa sổ cài đặt** — chuột phải bong bóng → Cài đặt: ngôn ngữ đích, chu kỳ quét, độ nhạy. Lưu là áp dụng ngay.
- OCR chạy **trên máy** (RapidOCR/ONNX — không cần gói ngôn ngữ OCR của Windows); dịch bằng Google Translate (miễn phí).

## Cài đặt

Yêu cầu Windows 10/11 và Python 3.10+.

```
git clone https://github.com/Compal123/dich-man-hinh.git
cd dich-man-hinh
python -m venv .venv
.venv\Scripts\pip install -r requirements.txt
```

## Chạy

Nhấp đúp `run.bat` (hoặc chạy `.venv\Scripts\python.exe main.py` để xem log lỗi).

- **Nhấn bong bóng** để chạy chế độ đang chọn (bật/tắt dịch sống / dịch một lần / dịch vùng).
- **Chuột phải** để đổi chế độ, mở cài đặt, xóa bộ nhớ dịch, hoặc thoát.
- **Kéo** bong bóng để di chuyển.

## Cách hoạt động

Chụp màn hình (mss) → kiểm tra màn hình còn đang thay đổi không (so khung hình, đang cuộn thì chờ) → OCR (RapidOCR) → bỏ qua dòng đã là ngôn ngữ đích → dịch các dòng chưa có trong bộ nhớ (Google) → vẽ ô bản dịch tại vị trí chữ gốc. Các cửa sổ overlay tự loại mình khỏi ảnh chụp màn hình (`WDA_EXCLUDEFROMCAPTURE`) nên máy quét không bao giờ đọc lại chính bản dịch của mình.

## Hướng phát triển (hoan nghênh ý tưởng & PR)

1. Chỉ OCR vùng màn hình thay đổi thay vì cả khung hình (giảm trễ).
2. Tùy chọn model dịch offline (bỏ phụ thuộc mạng).
3. Nút "dịch kỹ" cho đoạn văn quan trọng (LLM, hiểu ngữ cảnh/thuật ngữ).
4. Hỗ trợ nhiều màn hình.
5. Bản Android (bong bóng + MediaProjection).

## Giấy phép

MIT
