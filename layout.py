# -*- coding: utf-8 -*-
"""Thuật toán xếp chỗ và vẽ bản dịch đè lên vị trí chữ gốc.

Phần thuần thuật toán (không widget) - tách riêng để test được dễ dàng.
"""

import numpy as np
from PySide6.QtCore import QRect, QRectF, Qt
from PySide6.QtGui import QColor, QFont, QFontMetrics, QPen


def _v_overlap(a, b):
    return a.top() < b.bottom() and b.top() < a.bottom()


def _collides(box, obstacles):
    """box có đè lên chướng ngại nào không (chạm mép ≤2px thì cho qua,
    vì ô gốc đã được nới sẵn 1-2px để che kín chữ)."""
    b = box.adjusted(2, 2, -2, -2)
    for o in obstacles:
        if b.intersects(o):
            return True
    return False


def _layout_item(text, rl, obstacles, bounds):
    """Chọn chỗ vẽ cho một câu dịch (tiếng Việt thường dài hơn chữ gốc).

    Mọi ứng viên đều bị kiểm tra GIAO NHAU THẬT với các ô đã đặt và vị trí
    chữ gốc của các ô khác - trước đây chỉ ràng mép phải/mép dưới theo vài
    trường hợp nên các ô vẫn chồng đè nhau loạn xạ. Thử theo thứ tự:
    (1) một dòng tại chỗ, chữ to -> nhỏ, bề ngang theo chữ;
    (2) xuống dòng mở rộng xuống dưới nếu dưới còn trống;
    (3) hết cách thì cắt gọn có dấu "…" trong phần trống còn lại.
    Trả về (box, font, flags, text_để_vẽ).
    """
    MIN_PT = 8
    size = max(MIN_PT, min(24, int(rl.height() * 0.52)))
    font = QFont("Segoe UI", size)

    # 1. Một dòng tại chỗ: bề ngang ôm theo chữ (không hẹp hơn ô gốc kẻo
    # hở chữ gốc), miễn là không tràn màn hình và không đè ai
    for s in range(size, MIN_PT - 1, -1):
        font.setPointSize(s)
        w = QFontMetrics(font).horizontalAdvance(text) + 12
        box = QRectF(rl.left(), rl.top(), max(w, rl.width()), rl.height())
        if box.right() <= bounds.right() - 4 and not _collides(box, obstacles):
            return box, font, Qt.AlignVCenter | Qt.AlignLeft, text

    # Bề ngang trống tối đa: nới phải đến sát chướng ngại cùng hàng / mép màn
    max_right = bounds.right() - 4
    for b in obstacles:
        if _v_overlap(rl, b) and b.left() > rl.left():
            max_right = min(max_right, b.left() - 4)
    max_right = max(max_right, rl.right())  # không bao giờ hẹp hơn ô gốc
    avail_w = max_right - rl.left()

    # 2. Xuống dòng, mở rộng xuống dưới nếu bên dưới còn trống
    for s in range(min(size, 12), MIN_PT - 1, -1):
        font.setPointSize(s)
        fm = QFontMetrics(font)
        need = fm.boundingRect(QRect(0, 0, int(avail_w) - 12, 10000),
                               Qt.TextWordWrap, text)
        box = QRectF(rl.left(), rl.top(), avail_w,
                     max(need.height() + 8, rl.height()))
        if (box.bottom() <= bounds.bottom() - 4
                and not _collides(box, obstacles)):
            return (box, font,
                    Qt.AlignVCenter | Qt.AlignLeft | Qt.TextWordWrap, text)

    # 3. Hết cách: cắt gọn, có dấu "…" báo còn thiếu (rê chuột xem đủ)
    font.setPointSize(MIN_PT)
    fm = QFontMetrics(font)
    elided = fm.elidedText(text, Qt.ElideRight, int(avail_w) - 12)
    box = QRectF(rl.left(), rl.top(), avail_w, rl.height())
    return box, font, Qt.AlignVCenter | Qt.AlignLeft, elided


def coarse_shift(prev, cur):
    """Ước lượng THÔ cả màn hình trượt bao nhiêu giữa 2 khung (ảnh xám).

    Dùng để bắt cú cuộn/vẩy MẠNH: template khớp từng ô chỉ dò trong cửa sổ
    nhỏ nên vẩy nhanh là văng khỏi cửa sổ; ước lượng thô này cho trước hướng
    nhảy để dời cửa sổ dò theo. Cắt giữa 60% khung để taskbar/viền đứng im
    không đè kết quả về 0. Trả (dx, dy) ở đơn vị của ảnh truyền vào.
    """
    import cv2

    if prev is None or cur is None or prev.shape != cur.shape:
        return (0.0, 0.0)
    h, w = cur.shape[:2]
    y0, y1, x0, x1 = int(h * 0.2), int(h * 0.8), int(w * 0.2), int(w * 0.8)
    a = prev[y0:y1, x0:x1].astype(np.float32)
    b = cur[y0:y1, x0:x1].astype(np.float32)
    try:
        (dx, dy), conf = cv2.phaseCorrelate(a, b)
    except cv2.error:
        return (0.0, 0.0)
    if conf < 0.15 or abs(dx) > w or abs(dy) > h:
        return (0.0, 0.0)
    return (dx, dy)


def capture_templates(items, gray, scale=0.5, pad=7):
    """Cắt 'ảnh mẫu' vùng chữ gốc cho từng ô (để bám ở các khung sau).

    Mẫu lấy ở ảnh xám thu nhỏ (scale) + đệm thêm pad px quanh ô cho có bối
    cảnh (chữ trần trên nền phẳng dễ khớp nhầm nhiều chỗ). Lưu ngay vào item
    nên mẫu đi theo ô suốt vòng đời, set_items mới thì tự dựng lại.
    """
    hh, ww = gray.shape[:2]
    for it in items:
        r = it["rect"]
        sx, sy = int(r.x() * scale), int(r.y() * scale)
        sw, sh = max(6, int(r.width() * scale)), max(6, int(r.height() * scale))
        tx0, ty0 = max(0, sx - pad), max(0, sy - pad)
        tx1, ty1 = min(ww, sx + sw + pad), min(hh, sy + sh + pad)
        it["_tmpl"] = gray[ty0:ty1, tx0:tx1].copy()
        it["_anchor"] = (sx - tx0, sy - ty0)   # gốc ô nằm ở đâu trong mẫu
        it["_vel"] = (0.0, 0.0)
        it["_lost"] = 0


def _median(vals):
    s = sorted(vals)
    n = len(s)
    return s[n // 2] if n % 2 else (s[n // 2 - 1] + s[n // 2]) / 2


def track_frame(items, gray, prev_gray=None, scale=0.5, margin=20,
                thr=0.5, max_lost=8, tol=5, strong=0.8):
    """Dời mỗi ô theo khối chữ gốc của nó trong khung hình mới.

    Mỗi ô thử HAI giả thuyết chuyển động rồi lấy cái khớp cao hơn:
      (a) ô đi theo chuyển động RIÊNG của nó (vận tốc cũ; ô đứng yên -> 0 ->
          khớp ngay tại chỗ);
      (b) ô đi theo cú trượt THÔ của cả màn (bắt cú vẩy/cuộn mạnh khung đầu).
    Nhờ vậy một vùng cuộn độc lập (web cuộn) KHÔNG kéo được ô đứng yên (menu
    app) đi theo. Ô khớp MẠNH (>= strong) được tin hẳn kể cả khi lệch đám
    đông - đúng cho màn hình có nhiều vùng chuyển động khác nhau. Ô khớp yếu
    lệch mốc trung vị thì kéo về mốc (chống bám nhầm ô trùng chữ); ô mất dấu
    trôi theo mốc, quá max_lost khung không thấy thì rụng.
    Trả (list item còn sống, số ô khớp thật khung này).
    """
    import cv2

    hh, ww = gray.shape[:2]
    # Cú trượt thô của cả màn (đơn vị ảnh thu nhỏ đang xét) - chỉ dùng làm
    # một trong hai giả thuyết, không còn ép lên mọi ô như trước.
    gdx, gdy = coarse_shift(prev_gray, gray)

    def _match(tmpl, th, tw, ax, ay, r, seedx, seedy):
        """Khớp mẫu quanh vị trí dự đoán (cũ + seed). Trả (dx,dy,score) | None."""
        px = r.x() * scale - ax + seedx
        py = r.y() * scale - ay + seedy
        rx0, ry0 = max(0, int(px - margin)), max(0, int(py - margin))
        rx1, ry1 = min(ww, int(px + tw + margin)), min(hh, int(py + th + margin))
        vung = gray[ry0:ry1, rx0:rx1]
        if vung.shape[0] < th or vung.shape[1] < tw:
            return None
        res = cv2.matchTemplate(vung, tmpl, cv2.TM_CCOEFF_NORMED)
        _mn, mx, _ml, loc = cv2.minMaxLoc(res)
        if mx < thr:
            return None
        nsx, nsy = rx0 + loc[0] + ax, ry0 + loc[1] + ay
        return (nsx - r.x() * scale, nsy - r.y() * scale, mx)

    disp = []   # song song items: (dx_scaled, dy_scaled, score) hoặc None
    for it in items:
        tmpl = it.get("_tmpl")
        if tmpl is None or tmpl.shape[0] > hh or tmpl.shape[1] > ww:
            disp.append(None)
            continue
        th, tw = tmpl.shape[:2]
        ax, ay = it["_anchor"]
        vx, vy = it["_vel"]
        r = it["rect"]
        cands = [_match(tmpl, th, tw, ax, ay, r, vx, vy)]   # (a) chuyển động riêng
        if gdx or gdy:
            cands.append(_match(tmpl, th, tw, ax, ay, r, gdx, gdy))  # (b) trượt cả màn
        cands = [c for c in cands if c is not None]
        disp.append(max(cands, key=lambda c: c[2]) if cands else None)

    good = [d for d in disp if d is not None]
    bam = len(good)
    # Mốc chung = trung vị của các ô khớp MẠNH (nếu có), kẻo nhóm khớp yếu/
    # vùng chuyển động thiểu số kéo lệch mốc.
    ref = [d for d in good if d[2] >= strong] or good
    if ref:
        med = (_median([d[0] for d in ref]), _median([d[1] for d in ref]))
    else:
        med = None

    song = []
    for it, d in zip(items, disp):
        r = it["rect"]
        if d is not None and d[2] >= strong:
            dùng = (d[0], d[1])            # khớp chắc -> tin nó, kể cả khác đám đông
            it["_lost"] = 0
        elif d is not None and (med is None
                                or (abs(d[0] - med[0]) <= tol
                                    and abs(d[1] - med[1]) <= tol)):
            dùng = (d[0], d[1])            # khớp yếu nhưng hợp đám đông -> theo nó
            it["_lost"] = 0
        elif med is not None:
            dùng = med                     # bám nhầm/không thấy -> theo mốc chung
            it["_lost"] = it["_lost"] + 1 if d is None else 0
        else:
            # cả đám mất dấu (vẩy rất mạnh): trôi theo mốc thô nếu có,
            # không thì theo vận tốc cũ - chờ khung sau bắt lại
            it["_lost"] += 1
            dùng = (gdx, gdy) if (gdx or gdy) else it["_vel"]
        if d is None and it["_lost"] > max_lost:
            continue                        # mất dấu quá lâu -> rụng
        ndx = int(round(dùng[0] / scale))
        ndy = int(round(dùng[1] / scale))
        r.translate(ndx, ndy)
        it["_vel"] = (ndx * scale, ndy * scale)
        song.append(it)
    return song, bam


def _blocks(pending):
    """Chia các ô thành 'khối đoạn văn' dùng chung một nền.

    Hai dòng về chung khối khi sát nhau theo chiều dọc (hở dưới ~1/3 chiều
    cao dòng - phụ đề, đoạn chat, đoạn mô tả nhiều dòng) và chồng ngang
    đáng kể (>=40% bề ngang dòng hẹp hơn). Nền chung che kín chữ gốc cả
    khối nên các dòng bên trong được phép xê dịch nhẹ mà không hở chữ gốc.
    Trả list khối, mỗi khối là list chỉ số vào pending (đã theo thứ tự đọc).
    """
    blocks = []   # mỗi khối: {"u": QRectF bao cả khối, "idx": [chỉ số]}
    for i, (_t, rl) in enumerate(pending):
        chon = None
        for b in blocks:
            u = b["u"]
            if rl.top() - u.bottom() > 0.35 * rl.height():
                continue  # hở dọc quá xa
            ngang = min(u.right(), rl.right()) - max(u.left(), rl.left())
            if ngang < 0.4 * min(u.width(), rl.width()):
                continue  # gần như không chồng ngang (hai cột cạnh nhau)
            chon = b
            break
        if chon is None:
            blocks.append({"u": QRectF(rl), "idx": [i]})
        else:
            chon["idx"].append(i)
            chon["u"] = chon["u"].united(rl)
    return [b["idx"] for b in blocks]


def layout_boxes(items, dpr, bounds):
    """Tính chỗ vẽ cho mọi ô bản dịch - phần thuần, test được không cần vẽ.

    Các dòng sát nhau gộp thành khối chung một nền; trong khối, dòng dưới
    chớm đè dòng trên thì bị đẩy xuống ngay dưới (nền chung đã che kín chữ
    gốc nên xê dịch vài px không hở gì). Khối xếp theo thứ tự đọc, khối sau
    tự né khối trước. Trả list (panel, lines): panel = nền chung (QRectF),
    lines = list (box, font, flags, chữ_để_vẽ, nguyên_văn).
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
    pending.sort(key=lambda tr: (tr[1].top(), tr[1].left()))

    bases = [rl for _t, rl in pending]
    placed = []   # panel các khối đã đặt
    out = []
    for idx_list in _blocks(pending):
        trong = set(idx_list)
        # Chướng ngại = chữ gốc các ô NGOÀI khối + nền các khối đã đặt
        # (chữ gốc trong khối sẽ bị nền chung che nên không cần né)
        ngoai = [b for j, b in enumerate(bases) if j not in trong] + placed
        lines = []
        prev_bottom = None
        panel = None
        for i in idx_list:
            text, rl = pending[i]
            rl = QRectF(rl)
            if prev_bottom is not None and rl.top() < prev_bottom:
                rl.moveTop(prev_bottom)  # dòng dưới tụt khỏi đè dòng trên
            obstacles = ngoai + [ln[0] for ln in lines]
            box, font, flags, shown = _layout_item(text, rl, obstacles, bounds)
            lines.append((box, font, flags, shown, text))
            prev_bottom = box.bottom() + 1
            panel = box if panel is None else panel.united(box)
        for i in idx_list:
            panel = panel.united(pending[i][1])  # nền phải che kín chữ gốc
        placed.append(panel)
        out.append((panel, lines))
    return out


def draw_items(painter, items, dpr, bounds, bg=None, fg=None):
    """Vẽ các ô bản dịch đè lên vị trí chữ gốc.

    Dòng sát nhau chung một tấm nền (khối); vẽ 2 lượt - toàn bộ nền trước,
    toàn bộ chữ sau - nên nền không bao giờ đè lên chữ, kể cả ca chật chội.
    bg/fg là màu nền ô và màu chữ (QColor); thiếu thì dùng màu mặc định.
    Trả về list (box, nguyên_văn, bị_cắt) để lớp kết quả bắt hover.
    """
    if bg is None:
        bg = QColor(24, 26, 38, 235)
    if fg is None:
        fg = QColor(240, 242, 250)
    khoi = layout_boxes(items, dpr, bounds)

    painter.setPen(Qt.NoPen)
    painter.setBrush(bg)
    for panel, _lines in khoi:
        painter.drawRoundedRect(panel, 5, 5)

    layout = []
    painter.setBrush(Qt.NoBrush)
    for _panel, lines in khoi:
        for box, font, flags, shown, text in lines:
            layout.append((box, text, shown != text))
            painter.setFont(font)
            painter.setPen(QPen(fg))
            # Nới trần/sàn 5px trong vùng cắt cho dấu tiếng Việt không cụt
            painter.save()
            painter.setClipRect(box.adjusted(0, -5, 0, 5))
            painter.drawText(box.adjusted(5, 0, -3, 0), flags, shown)
            painter.restore()
    return layout
