# -*- coding: utf-8 -*-
"""Kiểm tra nhanh pipeline OCR + dịch không cần giao diện."""

import sys

import numpy as np
import cv2

sys.stdout.reconfigure(encoding="utf-8")

from ocr import ocr_image
from translate import translate_lines

# Tạo ảnh trắng có chữ tiếng Anh
img = np.full((200, 900, 3), 255, dtype=np.uint8)
cv2.putText(img, "Hello world, this is a test", (30, 80),
            cv2.FONT_HERSHEY_SIMPLEX, 1.4, (0, 0, 0), 3)
cv2.putText(img, "Machine error: replace the battery", (30, 160),
            cv2.FONT_HERSHEY_SIMPLEX, 1.2, (0, 0, 0), 3)

print("1. Chay OCR...")
result = ocr_image(img)
texts = [text for _box, text, _score in result]
print("   OCR doc duoc:", texts)
assert texts, "OCR khong doc duoc chu nao!"

print("2. Dich sang tieng Viet...")
per_line, full = translate_lines(texts)
print("   Ket qua:", per_line if per_line else full)
assert full.strip(), "Dich that bai!"

print("OK - pipeline hoat dong.")
