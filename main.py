# -*- coding: utf-8 -*-
"""
Dịch Màn Hình - bong bóng nổi dịch toàn màn hình sang tiếng Việt.

Hai chế độ:
- Nhấn bong bóng: BẬT/TẮT chế độ dịch sống - quét màn hình liên tục,
  bản dịch đè lên chữ gốc, chuột bấm xuyên qua, dùng app bên dưới bình thường.
- Chuột phải > "Dịch một lần": chụp - dịch - hiện kết quả, nhấn để đóng.
"""

import ctypes
import html
import json
import os
import sys
import threading
import traceback

import cv2
import numpy as np
from mss import mss
from PySide6.QtCore import QObject, QRect, QRectF, Qt, QTimer, Signal
from PySide6.QtGui import QColor, QFont, QFontMetrics, QPainter, QPen
from PySide6.QtWidgets import QApplication, QMenu, QTextEdit, QWidget

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
SETTINGS_FILE = os.path.join(BASE_DIR, "cai-dat.json")

_DEFAULT_SETTINGS = {
    "ngon_ngu_dich": "vi",     # dịch sang ngôn ngữ nào
    "do_tin_cay_ocr": 0.45,    # bỏ qua chữ OCR đọc kém tin cậy hơn mức này
    "chu_ky_quet_ms": 500,     # bao lâu quét màn hình một lần (mili giây)
    "nguong_thay_doi": 1.5,    # màn hình đổi hơn mức này = "đang cuộn/chuyển"
}


def _load_settings():
    s = dict(_DEFAULT_SETTINGS)
    try:
        with open(SETTINGS_FILE, encoding="utf-8") as f:
            s.update(json.load(f))
    except Exception:
        try:
            with open(SETTINGS_FILE, "w", encoding="utf-8") as f:
                json.dump(_DEFAULT_SETTINGS, f, ensure_ascii=False, indent=2)
        except Exception:
            pass
    return s


SETTINGS = _load_settings()
TARGET_LANG = str(SETTINGS["ngon_ngu_dich"])
MIN_OCR_SCORE = float(SETTINGS["do_tin_cay_ocr"])
CHUNK_LIMIT = 4000       # giới hạn ký tự mỗi lần gọi Google Dịch
LIVE_INTERVAL_MS = int(SETTINGS["chu_ky_quet_ms"])
DIFF_THRESHOLD = float(SETTINGS["nguong_thay_doi"])

_ocr_engine = None
_ocr_lock = threading.Lock()

# Bộ nhớ dịch: chữ gốc -> bản dịch. Lưu xuống file nên tắt app vẫn nhớ,
# dùng càng lâu càng ít phải gọi mạng.
CACHE_FILE = os.path.join(BASE_DIR, "bo-nho-dich.json")
_cache = {}
_cache_lock = threading.Lock()


def load_cache():
    try:
        with open(CACHE_FILE, encoding="utf-8") as f:
            _cache.update(json.load(f))
    except Exception:
        pass


def save_cache():
    with _cache_lock:
        try:
            tmp = CACHE_FILE + ".tmp"
            with open(tmp, "w", encoding="utf-8") as f:
                json.dump(_cache, f, ensure_ascii=False)
            os.replace(tmp, CACHE_FILE)
        except Exception:
            pass


def clear_cache():
    _cache.clear()
    try:
        os.remove(CACHE_FILE)
    except OSError:
        pass

_VI_DIACRITICS = set(
    "ăâđêôơưàảãáạằẳẵắặầẩẫấậèẻẽéẹềểễếệìỉĩíịòỏõóọồổỗốộờởỡớợùủũúụừửữứựỳỷỹýỵ")


def should_translate(text):
    """Bỏ qua dòng toàn số/ký hiệu và dòng đã là tiếng Việt (khỏi che, khỏi dịch)."""
    low = text.lower()
    if not any(c.isalpha() for c in low):
        return False
    if any(c in _VI_DIACRITICS for c in low):
        return False
    return True


def get_ocr():
    """Khởi tạo RapidOCR một lần duy nhất (lần đầu mất vài giây)."""
    global _ocr_engine
    with _ocr_lock:
        if _ocr_engine is None:
            from rapidocr import RapidOCR
            _ocr_engine = RapidOCR()
        return _ocr_engine


def ocr_image(img_bgr):
    """Chạy OCR, trả về list (box, text, score) thống nhất cho rapidocr v2."""
    result = get_ocr()(img_bgr)
    if result is None or result.txts is None:
        return []
    return list(zip(result.boxes, result.txts, result.scores))


def translate_lines(lines):
    """Dịch danh sách dòng chữ sang tiếng Việt.

    Trả về (per_line, full_text): per_line là list cùng độ dài với lines
    nếu Google giữ nguyên số dòng, ngược lại per_line = None.
    """
    from deep_translator import GoogleTranslator

    translator = GoogleTranslator(source="auto", target=TARGET_LANG)

    chunks, current, current_len = [], [], 0
    for line in lines:
        if current and current_len + len(line) + 1 > CHUNK_LIMIT:
            chunks.append(current)
            current, current_len = [], 0
        current.append(line)
        current_len += len(line) + 1
    if current:
        chunks.append(current)

    out_lines = []
    aligned = True
    full_parts = []
    for chunk in chunks:
        translated = html.unescape(translator.translate("\n".join(chunk)) or "")
        full_parts.append(translated)
        parts = [p.strip() for p in translated.split("\n")]
        if len(parts) == len(chunk):
            out_lines.extend(parts)
        else:
            aligned = False
    return (out_lines if aligned and len(out_lines) == len(lines) else None,
            "\n".join(full_parts))


def translate_cached(lines):
    """Dịch qua cache: chỉ gọi mạng cho dòng chưa gặp, luôn khớp từng dòng."""
    missing = [ln for ln in dict.fromkeys(lines) if ln not in _cache]
    if missing:
        per_line, _full = translate_lines(missing)
        if per_line is None:
            # Google gộp/tách dòng -> dịch từng dòng một cho chắc
            from deep_translator import GoogleTranslator
            translator = GoogleTranslator(source="auto", target=TARGET_LANG)
            per_line = []
            for ln in missing:
                try:
                    per_line.append(html.unescape(translator.translate(ln) or ln))
                except Exception:
                    per_line.append(ln)
        for src, dst in zip(missing, per_line):
            _cache[src] = dst
        save_cache()
    return [_cache.get(ln, ln) for ln in lines]


def extract_items(img_bgr):
    """OCR ảnh -> list item {rect, src, dst=''} (tọa độ pixel vật lý)."""
    items = []
    for box, text, score in ocr_image(img_bgr):
        text = (text or "").strip()
        if not text or float(score) < MIN_OCR_SCORE or not should_translate(text):
            continue
        xs = [p[0] for p in box]
        ys = [p[1] for p in box]
        items.append({
            "rect": QRect(int(min(xs)), int(min(ys)),
                          int(max(xs) - min(xs)), int(max(ys) - min(ys))),
            "src": text,
            "dst": "",
        })
    return items


def exclude_from_capture(widget):
    """Loại cửa sổ khỏi ảnh chụp màn hình (Windows 10 2004+).

    Nhờ vậy vòng quét sau vẫn thấy chữ gốc chứ không thấy bản dịch của chính app.
    """
    WDA_EXCLUDEFROMCAPTURE = 0x11
    try:
        return bool(ctypes.windll.user32.SetWindowDisplayAffinity(
            int(widget.winId()), WDA_EXCLUDEFROMCAPTURE))
    except Exception:
        return False


def grab_screen():
    """Chụp màn hình chính, trả về ảnh BGR."""
    with mss() as sct:
        shot = sct.grab(sct.monitors[1])
        return np.array(shot)[:, :, :3].copy()


class WorkerSignals(QObject):
    done = Signal(dict)
    error = Signal(str)


def run_job(img_bgr, signals, live=False):
    """Chạy trong thread nền: OCR rồi dịch (có cache), 2 pha ở chế độ sống."""
    try:
        items = extract_items(img_bgr)
        if live and items:
            # Pha 1: dòng nào đã có trong cache thì hiện NGAY, khỏi chờ mạng
            for it in items:
                it["dst"] = _cache.get(it["src"], "")
            if any(it["dst"] for it in items):
                signals.done.emit({"items": [dict(it) for it in items],
                                   "final": False})
        if items:
            for item, dst in zip(items, translate_cached([i["src"] for i in items])):
                item["dst"] = dst
        signals.done.emit({"items": items, "final": True})
    except Exception:
        signals.error.emit(traceback.format_exc(limit=3))


def draw_items(painter, items, dpr):
    """Vẽ các ô bản dịch đè lên vị trí chữ gốc."""
    for it in items:
        if not it["dst"]:
            continue  # chưa có bản dịch (đang chờ mạng) thì chưa vẽ
        r = it["rect"]
        rl = QRectF(r.x() / dpr, r.y() / dpr,
                    r.width() / dpr, r.height() / dpr).adjusted(-3, -2, 3, 2)
        painter.setPen(Qt.NoPen)
        painter.setBrush(QColor(24, 26, 38, 235))
        painter.drawRoundedRect(rl, 4, 4)

        # Cỡ chữ chừa chỗ cho dấu tiếng Việt (ấ, ề, ữ...), không vẽ sát trần ô
        size = max(8, min(24, int(rl.height() * 0.52)))
        font = QFont("Segoe UI", size)
        while size > 8:
            font.setPointSize(size)
            if QFontMetrics(font).horizontalAdvance(it["dst"]) <= rl.width() - 6:
                break
            size -= 1
        painter.setFont(font)
        painter.setPen(QPen(QColor(240, 242, 250)))
        # TextDontClip: không cắt phần dấu nhô ra ngoài ô -> hết "lỗi font"
        painter.drawText(rl, Qt.AlignVCenter | Qt.AlignLeft | Qt.TextDontClip,
                         " " + it["dst"])


class LiveOverlay(QWidget):
    """Lớp dịch sống: luôn hiện, chuột bấm xuyên qua, tự cập nhật."""

    def __init__(self):
        super().__init__()
        self.items = []
        self.dpr = 1.0
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint |
                            Qt.Tool | Qt.WindowTransparentForInput |
                            Qt.WindowDoesNotAcceptFocus)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setAttribute(Qt.WA_ShowWithoutActivating)
        self.setGeometry(QApplication.primaryScreen().geometry())

    def set_items(self, items):
        self.items = items
        self.dpr = QApplication.primaryScreen().devicePixelRatio() or 1.0
        self.update()

    def paintEvent(self, _event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        draw_items(p, self.items, self.dpr)
        p.end()


class ResultOverlay(QWidget):
    """Màn kết quả 'dịch một lần': nhấn chuột / Esc để đóng."""

    def __init__(self, items, panel_text, dpr):
        super().__init__()
        self.items = items
        self.dpr = dpr or 1.0
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setGeometry(QApplication.primaryScreen().geometry())

        if panel_text:
            box = QTextEdit(self)
            box.setReadOnly(True)
            box.setPlainText(panel_text)
            box.setStyleSheet(
                "QTextEdit{background:#1e1e28;color:#f0f0f5;border-radius:12px;"
                "padding:18px;font-size:15px;font-family:'Segoe UI';}")
            g = self.geometry()
            w = min(760, g.width() - 120)
            h = min(560, g.height() - 160)
            box.setGeometry((g.width() - w) // 2, (g.height() - h) // 2, w, h)

    def paintEvent(self, _event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        p.fillRect(self.rect(), QColor(10, 10, 16, 110))
        draw_items(p, self.items, self.dpr)
        p.setFont(QFont("Segoe UI", 11))
        p.setPen(QPen(QColor(255, 255, 255, 180)))
        p.drawText(QRectF(0, self.height() - 46, self.width(), 30),
                   Qt.AlignCenter, "Nhấn chuột hoặc Esc để đóng")
        p.end()

    def mousePressEvent(self, _event):
        self.close()

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Escape:
            self.close()


class Bubble(QWidget):
    """Bong bóng nổi: nhấn = bật/tắt dịch sống, kéo = di chuyển, chuột phải = menu."""

    SIZE = 58

    def __init__(self):
        super().__init__()
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint |
                            Qt.Tool)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setFixedSize(self.SIZE, self.SIZE)

        screen = QApplication.primaryScreen().geometry()
        self.move(screen.right() - self.SIZE - 14,
                  screen.top() + screen.height() // 3)

        self.live_on = False
        self.busy = False
        self.capture_safe = False   # True nếu Windows hỗ trợ loại overlay khỏi ảnh chụp
        self.prev_small = None      # ảnh thu nhỏ của lần quét trước, để so thay đổi
        self.screen_dirty = True    # màn hình có nội dung mới chưa dịch
        self.spin_angle = 0

        self.spin_timer = QTimer(self)
        self.spin_timer.timeout.connect(self._spin)
        self.live_timer = QTimer(self)
        self.live_timer.timeout.connect(self.live_tick)

        self.signals = WorkerSignals()
        self.signals.done.connect(self.on_done)
        self.signals.error.connect(self.on_error)

        self.live_overlay = None
        self.result_overlay = None
        self._pending_single = False
        self._press_pos = None
        self._dragged = False

    # ----- vẽ bong bóng -----
    def paintEvent(self, _event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        if self.live_on:
            color = QColor(46, 160, 90)      # xanh lá: đang dịch sống
        elif self.busy:
            color = QColor(230, 126, 34)     # cam: đang xử lý
        else:
            color = QColor(52, 120, 246)     # xanh dương: chờ
        p.setBrush(color)
        p.setPen(QPen(QColor(255, 255, 255, 60), 2))
        p.drawEllipse(3, 3, self.SIZE - 6, self.SIZE - 6)

        if self.busy:
            p.setPen(QPen(QColor(255, 255, 255), 3))
            p.drawArc(12, 12, self.SIZE - 24, self.SIZE - 24,
                      self.spin_angle * 16, 100 * 16)
        else:
            p.setPen(QPen(QColor(255, 255, 255)))
            p.setFont(QFont("Segoe UI", 10, QFont.Bold))
            p.drawText(self.rect(), Qt.AlignCenter,
                       "ON" if self.live_on else "Dịch")
        p.end()

    def _spin(self):
        self.spin_angle = (self.spin_angle - 24) % 360
        self.update()

    def _set_busy(self, value):
        self.busy = value
        if value:
            self.spin_timer.start(30)
        else:
            self.spin_timer.stop()
        self.update()

    # ----- chuột -----
    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self._press_pos = event.globalPosition().toPoint()
            self._offset = self._press_pos - self.frameGeometry().topLeft()
            self._dragged = False
        elif event.button() == Qt.RightButton:
            menu = QMenu(self)
            menu.addAction("Dịch một lần", self.single_shot)
            menu.addAction("Mở file cài đặt", lambda: os.startfile(SETTINGS_FILE))
            menu.addAction("Xóa bộ nhớ dịch", clear_cache)
            menu.addSeparator()
            menu.addAction("Thoát", QApplication.instance().quit)
            menu.exec(event.globalPosition().toPoint())

    def mouseMoveEvent(self, event):
        if self._press_pos is None:
            return
        pos = event.globalPosition().toPoint()
        if (pos - self._press_pos).manhattanLength() > 6:
            self._dragged = True
            self.move(pos - self._offset)

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.LeftButton:
            if not self._dragged:
                self.toggle_live()
            self._press_pos = None

    # ----- chế độ dịch sống -----
    def toggle_live(self):
        if self.live_on:
            self.stop_live()
        else:
            self.start_live()

    def start_live(self):
        self.live_on = True
        self.prev_small = None
        self.screen_dirty = True
        if self.live_overlay is None:
            self.live_overlay = LiveOverlay()
        self.live_overlay.show()
        self.capture_safe = exclude_from_capture(self.live_overlay)
        exclude_from_capture(self)
        self.live_timer.start(LIVE_INTERVAL_MS)
        self.update()
        self.live_tick()

    def stop_live(self):
        self.live_on = False
        self.live_timer.stop()
        if self.live_overlay is not None:
            self.live_overlay.set_items([])
            self.live_overlay.hide()
        self.update()

    def _grab_for_ocr(self):
        """Chụp màn hình; nếu Windows không tự loại overlay thì ẩn nó lúc chụp."""
        hidden = []
        if not self.capture_safe:
            for w in (self.live_overlay, self):
                if w is not None and w.isVisible():
                    w.hide()
                    hidden.append(w)
            QApplication.processEvents()
        try:
            return grab_screen()
        finally:
            for w in hidden:
                w.show()

    def live_tick(self):
        if self.busy or not self.live_on:
            return
        img = self._grab_for_ocr()

        # Màn hình gần như không đổi -> giữ nguyên overlay, khỏi quét lại
        small = cv2.resize(cv2.cvtColor(img, cv2.COLOR_BGR2GRAY), (160, 90))
        if self.prev_small is None:
            self.prev_small = small
            return
        moving = float(np.mean(cv2.absdiff(small, self.prev_small))) >= DIFF_THRESHOLD
        self.prev_small = small

        if moving:
            # Đang cuộn/chuyển màn hình: xóa bản dịch cũ và CHƯA quét vội.
            # Chờ màn hình đứng yên mới dịch - khỏi tốn công dịch cảnh lướt qua.
            if self.live_overlay is not None:
                self.live_overlay.set_items([])
            self.screen_dirty = True
            return

        if not self.screen_dirty:
            return  # màn hình đứng yên và đã dịch xong rồi

        self.screen_dirty = False
        self._set_busy(True)
        threading.Thread(target=run_job, args=(img, self.signals, True),
                         daemon=True).start()

    # ----- dịch một lần -----
    def single_shot(self):
        if self.busy:
            return
        self._pending_single = True
        exclude_from_capture(self)
        img = self._grab_for_ocr()
        self._set_busy(True)
        threading.Thread(target=run_job, args=(img, self.signals),
                         daemon=True).start()

    # ----- nhận kết quả -----
    def on_done(self, payload):
        items = payload["items"]
        if not payload.get("final", True):
            # Pha 1 (cache) ở chế độ sống: cập nhật overlay, vẫn đang xử lý tiếp
            if self.live_on and self.live_overlay is not None:
                self.live_overlay.set_items(items)
            return
        self._set_busy(False)
        if self._pending_single:
            self._pending_single = False
            dpr = QApplication.primaryScreen().devicePixelRatio()
            panel = "" if items else "Không tìm thấy chữ nào trên màn hình."
            self.result_overlay = ResultOverlay(items, panel, dpr)
            self.result_overlay.show()
            self.result_overlay.raise_()
            self.result_overlay.activateWindow()
        elif self.live_on and self.live_overlay is not None:
            self.live_overlay.set_items(items)

    def on_error(self, message):
        self._set_busy(False)
        self._pending_single = False
        self.stop_live()
        self.result_overlay = ResultOverlay(
            [], "Lỗi khi dịch. Kiểm tra kết nối mạng rồi thử lại.\n\n" + message,
            1.0)
        self.result_overlay.show()


def main():
    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)
    load_cache()

    bubble = Bubble()
    bubble.show()

    # Làm nóng OCR ở nền để cú nhấn đầu tiên không phải chờ lâu
    threading.Thread(target=get_ocr, daemon=True).start()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
