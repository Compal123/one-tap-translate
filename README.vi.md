# One Tap Translate (OTT)

🇬🇧 [English version here](README.md)

Bong bóng nổi trên Windows dịch chữ trên màn hình — game, app, tài liệu, bất cứ thứ gì bạn đang nhìn — và đè bản dịch lên đúng vị trí chữ gốc.

## Tính năng

- **Dịch live** — quét màn hình liên tục, bản dịch đè tại chỗ. Chuột bấm xuyên qua lớp dịch nên bạn dùng thứ bên dưới bình thường. Chờ màn hình đứng yên mới dịch (không tốn công dịch cảnh đang cuộn).
- **Dịch một lần** — nhấn bong bóng, xem ảnh chụp màn hình đã dịch, nhấn để đóng.
- **Dịch vùng chọn** — kéo khoanh một vùng, chỉ dịch vùng đó.
- **Màn hình nhiều ngôn ngữ** — các dòng được gom theo hệ chữ (Latin / Hán / Nhật / Hàn / Nga...) và mỗi nhóm được chỉ định thẳng ngôn ngữ nguồn khi dịch, nên nhiều ngôn ngữ trên cùng màn hình đều dịch đúng — kể cả tiếng Trung phồn thể.
- **Cửa sổ cài đặt** — chuột phải bong bóng: ngôn ngữ đích (Việt, Anh, Trung, Nhật, Hàn, Nga), chu kỳ quét, độ nhạy, **màu nền & màu chữ bản dịch**. Lưu là áp dụng ngay.
- **Phím tắt toàn cục** — `Ctrl + Alt + M` đổi chế độ, `Ctrl + Alt + T` chạy chế độ đang chọn (thay cho nhấn bong bóng). Dùng được cả khi đang trong game/app khác. Bật/tắt trong Cài đặt.
- OCR chạy trên máy của bạn bằng **PP-OCRv5** (bộ detect+recognize của PaddleOCR, chạy trên GPU, nhẹ & nhanh); dịch bằng Google Translate (hoặc Gemini/Groq nếu nhập key).

## Tải về & cài nhanh

Tải `OneTapTranslate-v1.2.0.zip` ở [bản phát hành mới nhất](https://github.com/Compal123/one-tap-translate/releases/latest), giải nén ra đâu cũng được, rồi:

1. Nhấp đúp **`setup.bat`** — tự cài thư viện cần thiết (sẽ hỏi bạn có GPU NVIDIA không).
2. Nhấp đúp **`run.bat`** để mở app. Lần chạy đầu tự tải model PP-OCRv5 (~22MB).

Yêu cầu: Windows 10/11 64-bit + **Python 3.12** (`setup.bat` sẽ nhắc nếu máy chưa có). Có GPU NVIDIA thì OCR nhanh hơn nhiều — không có vẫn chạy được bằng CPU.

> Gói tải về nhẹ (chỉ mã nguồn) — thư viện nặng (PaddlePaddle) và model được tải khi cài/chạy lần đầu, nên không kèm sẵn trong file zip.

## Cài đặt từ mã nguồn

Yêu cầu Windows 10/11, **Python 3.12** (PaddlePaddle chưa hỗ trợ 3.13/3.14), và
nên có **GPU NVIDIA** (CUDA 12.x) để OCR chạy nhanh.

```
git clone https://github.com/Compal123/one-tap-translate.git
cd one-tap-translate
py -3.12 -m venv .venv

REM 1) PaddlePaddle (chọn theo phần cứng):
REM    - Có GPU NVIDIA (khuyên dùng):
.venv\Scripts\pip install paddlepaddle-gpu -i https://www.paddlepaddle.org.cn/packages/stable/cu126/
REM    - Chỉ có CPU (chậm hơn nhiều):
REM  .venv\Scripts\pip install paddlepaddle

REM 2) Phần còn lại:
.venv\Scripts\pip install -r requirements.txt
```

Lần chạy đầu, PP-OCRv5 tự tải model (~vài chục MB) về `%USERPROFILE%\.paddlex` — cần mạng một lần.

## Chạy

Nhấp đúp `run.bat` (hoặc chạy `.venv\Scripts\python.exe main.py` để xem log lỗi).

- **Nhấn bong bóng** để chạy chế độ đang chọn (bật/tắt dịch live / dịch một lần / dịch vùng).
- **Chuột phải** để đổi chế độ, mở cài đặt, hoặc thoát.
- **Kéo** bong bóng để di chuyển.
- **Phím tắt**: `Ctrl + Alt + M` đổi chế độ, `Ctrl + Alt + T` chạy (thay cho nhấn bong bóng).

## Giấy phép

MIT
