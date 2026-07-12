# One Tap Translate (OTT)

🇬🇧 [English version here](README.md)

Bong bóng nổi trên Windows dịch chữ trên màn hình — game, app, tài liệu, bất cứ thứ gì bạn đang nhìn — và đè bản dịch lên đúng vị trí chữ gốc.

## Tính năng

- **Dịch live** — quét màn hình liên tục, bản dịch đè tại chỗ. Chuột bấm xuyên qua lớp dịch nên bạn dùng thứ bên dưới bình thường. Chờ màn hình đứng yên mới dịch (không tốn công dịch cảnh đang cuộn).
- **Dịch một lần** — nhấn bong bóng, xem ảnh chụp màn hình đã dịch, nhấn để đóng.
- **Dịch vùng chọn** — kéo khoanh một vùng, chỉ dịch vùng đó.
- **Màn hình nhiều ngôn ngữ** — các dòng được gom theo hệ chữ (Latin / Hán / Nhật / Hàn / Nga...) và mỗi nhóm được chỉ định thẳng ngôn ngữ nguồn khi dịch, nên nhiều ngôn ngữ trên cùng màn hình đều dịch đúng — kể cả tiếng Trung phồn thể.
- **Cửa sổ cài đặt** — chuột phải bong bóng: ngôn ngữ đích (Việt, Anh, Trung, Nhật, Hàn, Nga), chu kỳ quét, độ nhạy. Lưu là áp dụng ngay.
- OCR chạy trên máy của bạn (RapidOCR/ONNX); dịch bằng Google Translate.

## Tải về (không cần cài Python)

Tải `OneTapTranslate-win64.zip` ở [bản phát hành mới nhất](https://github.com/Compal123/one-tap-translate/releases/latest), giải nén ra đâu cũng được, chạy `OneTapTranslate.exe`. Windows 10/11, 64-bit.

## Cài đặt từ mã nguồn

Yêu cầu Windows 10/11 và Python 3.10+.

```
git clone https://github.com/Compal123/one-tap-translate.git
cd one-tap-translate
python -m venv .venv
.venv\Scripts\pip install -r requirements.txt
```

## Chạy

Nhấp đúp `run.bat` (hoặc chạy `.venv\Scripts\python.exe main.py` để xem log lỗi).

- **Nhấn bong bóng** để chạy chế độ đang chọn (bật/tắt dịch live / dịch một lần / dịch vùng).
- **Chuột phải** để đổi chế độ, mở cài đặt, hoặc thoát.
- **Kéo** bong bóng để di chuyển.

## Giấy phép

MIT
