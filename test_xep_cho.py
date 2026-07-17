# -*- coding: utf-8 -*-
"""Test offline: gộp mảnh OCR cùng dòng + xếp chỗ bản dịch không chồng đè
+ dòng sát nhau gộp chung một nền (khối).

Chạy: python test_xep_cho.py (không cần màn hình - Qt chạy offscreen)"""

import os
import sys

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
sys.stdout.reconfigure(encoding="utf-8")

from PySide6.QtCore import QRect, QRectF
from PySide6.QtGui import QGuiApplication

app = QGuiApplication([])  # QFontMetrics cần app tồn tại

from layout import layout_boxes
from ocr import _gop_manh_cung_dong


def item(x, y, w, h, src, dst=""):
    return {"rect": QRect(x, y, w, h), "src": src, "dst": dst}


def cac_dong(kq):
    """Gom mọi dòng của mọi khối: list (box, font, flags, shown, text)."""
    return [ln for _panel, lines in kq for ln in lines]


def cap_de(boxes):
    """Các cặp box đè nhau (chạm mép <=2px cho qua như _collides)."""
    return [(i, j) for i in range(len(boxes)) for j in range(i + 1, len(boxes))
            if boxes[i].intersects(boxes[j].adjusted(2, 2, -2, -2))]


# ── 1. Gộp mảnh OCR cùng dòng ──────────────────────────────────────────
# Một câu bị OCR xé 3 mảnh (top lệch nhau 1px như thật) + 1 dòng dưới
# + 1 tiêu đề cao gấp đôi ngay cạnh (không được gộp vào)
manh = [
    item(100, 100, 80, 20, "Mô phỏng"),
    item(186, 101, 40, 19, "HMI"),
    item(232, 100, 150, 20, "trên 1 PC"),
    item(100, 140, 200, 20, "Dòng dưới không dính"),
    item(400, 95, 200, 40, "TIÊU ĐỀ TO"),
]
kq = _gop_manh_cung_dong(manh)
srcs = [it["src"] for it in kq]
assert "Mô phỏng HMI trên 1 PC" in srcs, srcs
assert "Dòng dưới không dính" in srcs, srcs
assert "TIÊU ĐỀ TO" in srcs, srcs
assert len(kq) == 3, srcs
r = next(it["rect"] for it in kq if it["src"].startswith("Mô phỏng"))
assert r.left() == 100 and r.right() >= 381, r  # rect ôm trọn cả 3 mảnh
print("1. Gộp mảnh cùng dòng: OK (5 mảnh -> %d ô, câu nối đúng thứ tự)" % len(kq))

# Hai cột cách xa nhau thì KHÔNG được gộp (label | giá trị)
xa = _gop_manh_cung_dong([
    item(100, 100, 80, 20, "Tốc độ"),
    item(400, 100, 60, 20, "Nhanh"),
])
assert len(xa) == 2, [it["src"] for it in xa]
print("2. Hai cột cách xa không bị gộp nhầm: OK")

# ── 2. Khối nền chung: 2 dòng phụ đề sát nhau (ca ảnh chụp của user) ───
sub = [
    item(50, 100, 260, 22, "old line 1", dst="Chuyện cũ nhờ anh theo dõi tôi,"),
    item(50, 124, 300, 22, "old line 2",
         dst="Bạn thực sự không bao giờ rời bỏ tôi."),
]
kq = layout_boxes(sub, 1.0, QRectF(0, 0, 500, 300))
assert len(kq) == 1, "2 dòng sát nhau phải về chung 1 khối, ra %d" % len(kq)
panel, lines = kq[0]
assert len(lines) == 2
b1, b2 = lines[0][0], lines[1][0]
assert b2.top() >= b1.bottom() - 0.5, (b1, b2)  # dòng dưới không đè dòng trên
assert panel.contains(b1) and panel.contains(b2)  # nền che kín cả 2 dòng
print("3. Phụ đề 2 dòng: 1 nền chung, dòng dưới nằm hẳn dưới dòng trên - OK")

# Hai dòng CÁCH XA (khác vùng màn hình) thì vẫn 2 khối riêng
roi = layout_boxes([
    item(50, 100, 260, 22, "a", dst="ô thứ nhất bản dịch"),
    item(50, 300, 260, 22, "b", dst="ô thứ hai bản dịch"),
], 1.0, QRectF(0, 0, 500, 400))
assert len(roi) == 2, len(roi)
print("4. Hai dòng cách xa vẫn 2 nền riêng: OK")

# ── 3. Lưới dày đặc, bản dịch dài hơn hẳn: không gì đè lên gì ──────────
items = []
for hang in range(8):
    for cot in range(3):
        items.append(item(
            20 + cot * 300, 30 + hang * 34, 180, 22,
            "line %d-%d" % (hang, cot),
            dst="bản dịch tiếng Việt dài hơn hẳn dòng gốc %d-%d" % (hang, cot)))
bounds = QRectF(0, 0, 1000, 700)
kq = layout_boxes(items, 1.0, bounds)
lines = cac_dong(kq)
assert len(lines) == len(items), (len(lines), len(items))
panels = [p for p, _ls in kq]
de = cap_de(panels)
assert not de, "%d cặp nền đè nhau: %s" % (len(de), de[:5])
de = cap_de([ln[0] for ln in lines])
assert not de, "%d cặp dòng đè nhau: %s" % (len(de), de[:5])
for p in panels:
    assert bounds.contains(p), p
print("5. Lưới %d ô dày đặc: nền và chữ đều 0 cặp đè nhau, không tràn màn - OK"
      % len(lines))

# ── 4. Ca bí: hàng rất sát + chữ rất dài -> chung nền, xếp dòng/cắt "…" ─
chat = []
for hang in range(5):
    chat.append(item(
        10, 10 + hang * 24, 150, 20, "row %d" % hang,
        dst="một đoạn dịch cực kỳ lê thê dài dòng văn tự không thể nào "
            "nhét vừa chỗ trống %d" % hang))
kq = layout_boxes(chat, 1.0, QRectF(0, 0, 400, 200))
lines = cac_dong(kq)
assert len(lines) == 5
de = cap_de([ln[0] for ln in lines])
assert not de, de
print("6. Hàng sát + chữ dài: %d khối, chữ không đè nhau - OK" % len(kq))

print("Tất cả test xếp chỗ OK.")
