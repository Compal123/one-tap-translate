# -*- coding: utf-8 -*-
"""Kiểm tra nhanh pipeline OCR + dịch không cần giao diện.

Chạy: python test_smoke.py [auto|paddle|rapid|windows]
(không truyền gì = backend theo cài đặt hiện tại)"""

import sys

import numpy as np
import cv2

sys.stdout.reconfigure(encoding="utf-8")

from ocr import active_backend, init_backend, ocr_image
from settings import SETTINGS, load_settings
from translate import translate_lines

load_settings()
if len(sys.argv) > 1:
    SETTINGS["ocr_backend"] = sys.argv[1]
init_backend()

# Tạo ảnh trắng có chữ tiếng Anh
img = np.full((200, 900, 3), 255, dtype=np.uint8)
cv2.putText(img, "Hello world, this is a test", (30, 80),
            cv2.FONT_HERSHEY_SIMPLEX, 1.4, (0, 0, 0), 3)
cv2.putText(img, "Machine error: replace the battery", (30, 160),
            cv2.FONT_HERSHEY_SIMPLEX, 1.2, (0, 0, 0), 3)

print("1. Chay OCR (backend: %s)..." % active_backend())
result = ocr_image(img)
texts = [text for _box, text, _score in result]
print("   OCR doc duoc:", texts)
assert texts, "OCR khong doc duoc chu nao!"

print("2. Dich sang tieng Viet...")
per_line, full = translate_lines(texts)
print("   Ket qua:", per_line if per_line else full)
assert full.strip(), "Dich that bai!"

print("OK - pipeline hoat dong.")
