# -*- coding: utf-8 -*-
"""Thuật toán xếp chỗ và vẽ bản dịch đè lên vị trí chữ gốc.

Phần thuần thuật toán (không widget) - tách riêng để test được dễ dàng.
"""

from PySide6.QtCore import QRect, QRectF, Qt
from PySide6.QtGui import QColor, QFont, QFontMetrics, QPen


def _v_overlap(a, b):
    return a.top() < b.bottom() and b.top() < a.bottom()


def _h_overlap(left, right, b):
    return b.left() < right and left < b.right()


def _layout_item(text, rl, others, bounds):
    """Chọn chỗ vẽ cho một câu dịch (tiếng Việt thường dài hơn chữ gốc).

    Thử theo thứ tự: (1) vừa ô gốc, (2) nhỏ chữ + nới sang phải đến sát
    ô khác/mép màn hình, (3) xuống dòng mở rộng xuống dưới nếu trống,
    (4) hết cách thì cắt gọn có dấu "…".
    Trả về (box, font, flags, text_để_vẽ).
    """
    MIN_PT = 8
    size = max(MIN_PT, min(24, int(rl.height() * 0.52)))
    font = QFont("Segoe UI", size)

    # 1. Vừa ô gốc (cho phép giảm tối đa 2 cỡ chữ)
    for s in range(size, max(MIN_PT, size - 2) - 1, -1):
        font.setPointSize(s)
        if QFontMetrics(font).horizontalAdvance(text) <= rl.width() - 8:
            return rl, font, Qt.AlignVCenter | Qt.AlignLeft, text

    # 2. Nới sang phải đến sát ô hàng xóm / mép màn hình
    max_right = bounds.right() - 4
    for b in others:
        if _v_overlap(rl, b) and b.left() > rl.left():
            max_right = min(max_right, b.left() - 4)
    max_right = max(max_right, rl.right())  # không bao giờ hẹp hơn ô gốc
    avail_w = max_right - rl.left()
    for s in range(size, MIN_PT - 1, -1):
        font.setPointSize(s)
        w = QFontMetrics(font).horizontalAdvance(text)
        if w <= avail_w - 8:
            box = QRectF(rl.left(), rl.top(), w + 12, rl.height())
            return box, font, Qt.AlignVCenter | Qt.AlignLeft, text

    # 3. Xuống dòng, mở rộng xuống dưới nếu bên dưới còn trống
    font.setPointSize(MIN_PT)
    fm = QFontMetrics(font)
    max_bottom = bounds.bottom() - 4
    for b in others:
        if b.top() >= rl.bottom() - 1 and _h_overlap(rl.left(), max_right, b):
            max_bottom = min(max_bottom, b.top() - 4)
    need = fm.boundingRect(QRect(0, 0, int(avail_w) - 12, 10000),
                           Qt.TextWordWrap, text)
    if rl.top() + need.height() + 8 <= max_bottom:
        box = QRectF(rl.left(), rl.top(), avail_w, need.height() + 8)
        return (box, font,
                Qt.AlignVCenter | Qt.AlignLeft | Qt.TextWordWrap, text)

    # 4. Hết cách: cắt gọn, có dấu "…" báo còn thiếu
    elided = fm.elidedText(text, Qt.ElideRight, int(avail_w) - 12)
    box = QRectF(rl.left(), rl.top(), avail_w, rl.height())
    return box, font, Qt.AlignVCenter | Qt.AlignLeft, elided


def draw_items(painter, items, dpr, bounds):
    """Vẽ các ô bản dịch đè lên vị trí chữ gốc, không ô nào đè lên ô nào.

    Trả về list (box, nguyên_văn, bị_cắt) để lớp kết quả bắt hover.
    """
    pending = []
    for it in items:
        if not it["dst"]:
            continue  # chưa có bản dịch (đang chờ mạng) thì chưa vẽ
        if it["dst"].strip().lower() == it.get("src", "").strip().lower():
            continue  # dịch ra y nguyên -> che chữ gốc chỉ tổ rối màn hình
        r = it["rect"]
        rl = QRectF(r.x() / dpr, r.y() / dpr,
                    r.width() / dpr, r.height() / dpr).adjusted(-2, -1, 2, 1)
        pending.append((it["dst"], rl))

    bases = [rl for _t, rl in pending]
    placed = []
    layout = []
    for idx, (text, rl) in enumerate(pending):
        others = [b for j, b in enumerate(bases) if j != idx] + placed
        box, font, flags, shown = _layout_item(text, rl, others, bounds)
        placed.append(box)
        layout.append((box, text, shown != text))

        painter.setPen(Qt.NoPen)
        painter.setBrush(QColor(24, 26, 38, 235))
        painter.drawRoundedRect(box, 4, 4)
        painter.setFont(font)
        painter.setPen(QPen(QColor(240, 242, 250)))
        # Nới trần/sàn 5px trong vùng cắt cho dấu tiếng Việt không cụt
        painter.save()
        painter.setClipRect(box.adjusted(0, -5, 0, 5))
        painter.drawText(box.adjusted(5, 0, -3, 0), flags, shown)
        painter.restore()
    return layout
