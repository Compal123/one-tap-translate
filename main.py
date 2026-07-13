# -*- coding: utf-8 -*-
"""
One Tap Translate (OTT) - bong bóng nổi dịch màn hình.

Ba chế độ (chuột phải bong bóng để chọn, app nhớ lựa chọn):
- Dịch live:     quét màn hình liên tục, bản dịch đè lên chữ gốc,
                 chuột bấm xuyên qua, dùng app bên dưới bình thường.
- Dịch một lần:  nhấn bong bóng -> chụp - dịch - hiện kết quả.
- Dịch vùng chọn: nhấn bong bóng -> kéo khoanh vùng -> chỉ dịch vùng đó.

Cấu trúc mã nguồn:
- settings.py  cài đặt (cai-dat.json) + chữ giao diện song ngữ
- ocr.py       đọc chữ từ ảnh (PP-OCRv5 detect+recognize, trên GPU)
- translate.py dịch Google + AI (Gemini/Groq) + bộ nhớ trong phiên
- winutil.py   tiện ích Windows (autostart, chụp màn hình...)
- worker.py    pipeline OCR -> dịch chạy thread nền
- layout.py    thuật toán xếp chỗ bản dịch trên màn hình
- ui.py        bong bóng, các overlay, cửa sổ cài đặt
"""

import os
import sys
import threading
import traceback

import cv2
import numpy as np
from PySide6.QtWidgets import QApplication

from ocr import extract_items, get_ocr
from settings import BASE_DIR, load_settings
from translate import translate_cached
from ui import Bubble


def _smoke(out_path):
    """Tự kiểm tra bản đóng gói: OCR ảnh mẫu rồi thử dịch, ghi kết quả ra file.

    Chạy: OneTapTranslate.exe --smoke (app cửa sổ không có console nên
    kết quả nằm trong smoke-ket-qua.txt cạnh exe). Mã thoát 0 = OCR ổn.
    """
    img = np.full((160, 760, 3), 255, dtype=np.uint8)
    cv2.putText(img, "Hello packaged world", (30, 90),
                cv2.FONT_HERSHEY_SIMPLEX, 1.4, (0, 0, 0), 3)
    lines = []
    note = []
    try:
        lines = [it["src"] for it in extract_items(img)]
        note.append("OCR: " + (repr(lines) if lines else "FAIL - khong doc duoc chu"))
    except Exception:
        note.append("OCR: LOI\n" + traceback.format_exc())
    if lines:
        try:
            note.append("Dich: " + repr(translate_cached(lines)))
        except Exception as e:
            note.append("Dich: loi (mang?): %r" % e)
    with open(out_path, "w", encoding="utf-8") as f:
        f.write("\n".join(note) + "\n")
    return 0 if lines else 1


def main():
    if "--smoke" in sys.argv:
        sys.exit(_smoke(os.path.join(BASE_DIR, "smoke-ket-qua.txt")))
    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)
    load_settings()

    bubble = Bubble()
    bubble.show()

    # Làm nóng OCR ở nền để cú nhấn đầu tiên không phải chờ lâu
    threading.Thread(target=get_ocr, daemon=True).start()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
