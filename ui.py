# -*- coding: utf-8 -*-
"""Giao diện: bong bóng nổi, các lớp overlay và cửa sổ cài đặt."""

import threading
import time

import cv2
import numpy as np
from PySide6.QtCore import QRect, QRectF, Qt, QTimer, QUrl, Signal
from PySide6.QtGui import (QBrush, QColor, QDesktopServices, QFont,
                           QFontMetrics, QPainter, QPen, QRadialGradient)
from PySide6.QtWidgets import (QApplication, QCheckBox, QComboBox, QDialog,
                               QDialogButtonBox, QDoubleSpinBox, QFormLayout,
                               QHBoxLayout, QLabel, QLineEdit, QMenu,
                               QPushButton, QSpinBox, QTabWidget, QTextEdit,
                               QVBoxLayout, QWidget)

from layout import capture_templates, draw_items, track_frame
from settings import (APP_NAME, APP_VERSION, GITHUB_URL, L, S, SETTINGS,
                      save_settings)
from translate import (GEMINI_KEY_PAGE, GROQ_KEY_PAGE, translate_gemini,
                       translate_groq)
from winutil import (autostart_enabled, exclude_from_capture, grab_screen,
                     set_autostart)
from worker import WorkerSignals, run_job


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
        draw_items(p, self.items, self.dpr, QRectF(self.rect()))
        p.end()


class ResultOverlay(QWidget):
    """Màn kết quả 'dịch một lần' / 'dịch vùng': nhấn chuột / Esc để đóng.

    Rê chuột vào ô bị cắt "…" để xem nguyên văn bản dịch đầy đủ.
    """

    def __init__(self, items, panel_text, dpr):
        super().__init__()
        self.items = items
        self.dpr = dpr or 1.0
        self._layout = []
        self._hover = None
        self.setMouseTracking(True)
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
        self._layout = draw_items(p, self.items, self.dpr, QRectF(self.rect()))
        p.setFont(QFont("Segoe UI", 11))
        p.setPen(QPen(QColor(255, 255, 255, 180)))
        p.drawText(QRectF(0, self.height() - 46, self.width(), 30),
                   Qt.AlignCenter, L("res_close_hint"))

        # Khung nổi hiện nguyên văn khi rê chuột vào ô bị cắt
        if self._hover is not None and self._hover < len(self._layout):
            box, text, _elided = self._layout[self._hover]
            font = QFont("Segoe UI", 11)
            fm = QFontMetrics(font)
            need = fm.boundingRect(QRect(0, 0, 520, 2000),
                                   Qt.TextWordWrap, text)
            pw, ph = need.width() + 24, need.height() + 18
            x = min(box.left(), self.width() - pw - 8)
            y = box.bottom() + 6
            if y + ph > self.height() - 8:
                y = box.top() - ph - 6
            pop = QRectF(max(8, x), max(8, y), pw, ph)
            p.setPen(QPen(QColor(90, 170, 255), 1.5))
            p.setBrush(QColor(20, 24, 40, 250))
            p.drawRoundedRect(pop, 8, 8)
            p.setFont(font)
            p.setPen(QPen(QColor(240, 242, 250)))
            p.drawText(pop.adjusted(12, 9, -12, -9),
                       Qt.AlignLeft | Qt.AlignTop | Qt.TextWordWrap, text)
        p.end()

    def mouseMoveEvent(self, event):
        pos = event.position()
        hover = None
        for i, (box, _text, elided) in enumerate(self._layout):
            if elided and box.contains(pos):
                hover = i
                break
        if hover != self._hover:
            self._hover = hover
            self.update()

    def mousePressEvent(self, _event):
        self.close()

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Escape:
            self.close()


class SelectionOverlay(QWidget):
    """Kéo chuột khoanh vùng cần dịch. Esc để hủy."""

    picked = Signal(QRect)  # tọa độ logic

    def __init__(self):
        super().__init__()
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setCursor(Qt.CrossCursor)
        self.setGeometry(QApplication.primaryScreen().geometry())
        self.origin = None
        self.current = None

    def paintEvent(self, _event):
        p = QPainter(self)
        p.fillRect(self.rect(), QColor(10, 10, 16, 90))
        if self.origin is not None and self.current is not None:
            sel = QRect(self.origin, self.current).normalized()
            # Đục lỗ vùng đang chọn cho nhìn rõ nội dung thật
            p.setCompositionMode(QPainter.CompositionMode_Clear)
            p.fillRect(sel, Qt.transparent)
            p.setCompositionMode(QPainter.CompositionMode_SourceOver)
            p.setPen(QPen(QColor(90, 170, 255), 2))
            p.setBrush(Qt.NoBrush)
            p.drawRect(sel)
        else:
            p.setFont(QFont("Segoe UI", 12))
            p.setPen(QPen(QColor(255, 255, 255, 200)))
            p.drawText(self.rect(), Qt.AlignCenter, L("sel_hint"))
        p.end()

    def mousePressEvent(self, event):
        self.origin = event.position().toPoint()
        self.current = self.origin
        self.update()

    def mouseMoveEvent(self, event):
        if self.origin is not None:
            self.current = event.position().toPoint()
            self.update()

    def mouseReleaseEvent(self, event):
        if self.origin is None:
            return
        sel = QRect(self.origin, self.current).normalized()
        self.close()
        if sel.width() > 10 and sel.height() > 10:
            self.picked.emit(sel)

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Escape:
            self.close()


class SettingsDialog(QDialog):
    """Cửa sổ cài đặt 4 tab: bấm Lưu là áp dụng ngay, không cần khởi động lại."""

    LANGS = [("Tiếng Việt", "vi"), ("English", "en"), ("中文", "zh-CN"),
             ("日本語", "ja"), ("한국어", "ko"), ("Русский", "ru")]
    UI_LANGS = [("Tiếng Việt", "vi"), ("English", "en")]

    _test_done = Signal(bool, str)  # kết quả kiểm tra key (từ thread nền)

    def __init__(self, on_saved):
        super().__init__()
        self.on_saved = on_saved
        self._test_done.connect(self._on_test_done)
        self.setWindowTitle(L("st_title"))
        self.setWindowFlags(self.windowFlags() | Qt.WindowStaysOnTopHint)
        self.setMinimumWidth(380)

        tabs = QTabWidget()

        # --- Tab Chung: ngôn ngữ + khởi động cùng Windows ---
        general = QWidget()
        form = QFormLayout(general)

        self.lang = QComboBox()
        for label, code in self.LANGS:
            self.lang.addItem(f"{label} ({code})", code)
        idx = self.lang.findData(S("ngon_ngu_dich"))
        self.lang.setCurrentIndex(idx if idx >= 0 else 0)
        form.addRow(L("st_target"), self.lang)

        self.ui_lang = QComboBox()
        for label, code in self.UI_LANGS:
            self.ui_lang.addItem(label, code)
        idx = self.ui_lang.findData(S("ngon_ngu_giao_dien"))
        self.ui_lang.setCurrentIndex(idx if idx >= 0 else 0)
        form.addRow(L("st_ui_lang"), self.ui_lang)

        self.autostart = QCheckBox(L("st_autostart"))
        self.autostart.setChecked(autostart_enabled())
        form.addRow("", self.autostart)

        tabs.addTab(general, L("tab_general"))

        # --- Tab Quét & OCR ---
        scan = QWidget()
        form = QFormLayout(scan)

        self.interval = QSpinBox()
        self.interval.setRange(100, 5000)
        self.interval.setSingleStep(100)
        self.interval.setSuffix(" ms")
        self.interval.setValue(int(S("chu_ky_quet_ms")))
        form.addRow(L("st_interval"), self.interval)

        self.threshold = QDoubleSpinBox()
        self.threshold.setRange(0.1, 20.0)
        self.threshold.setSingleStep(0.1)
        self.threshold.setValue(float(S("nguong_thay_doi")))
        form.addRow(L("st_threshold"), self.threshold)

        self.score = QDoubleSpinBox()
        self.score.setRange(0.05, 1.0)
        self.score.setSingleStep(0.05)
        self.score.setValue(float(S("do_tin_cay_ocr")))
        form.addRow(L("st_score"), self.score)

        self.ocr_quality = QComboBox()
        self.ocr_quality.addItem(L("ocr_fast"), "nhanh")
        self.ocr_quality.addItem(L("ocr_accurate"), "chinh_xac")
        idx = self.ocr_quality.findData(S("ocr_chat_luong"))
        self.ocr_quality.setCurrentIndex(idx if idx >= 0 else 0)
        form.addRow(L("st_ocr_quality"), self.ocr_quality)

        tabs.addTab(scan, L("tab_scan"))

        # --- Tab Engine dịch (chọn riêng từng chế độ) ---
        ai = QWidget()
        form = QFormLayout(ai)

        # Mỗi chế độ một combo engine riêng. "Gemini nhìn ảnh" (vision) chỉ
        # cho một lần / vùng chọn - live cần nhanh nên không có lựa chọn này.
        self.engine_combos = {}
        for mode in ("song", "mot_lan", "vung"):
            combo = QComboBox()
            codes = ["groq", "gemini", "google"]
            if mode != "song":
                codes.append("vision")
            for code in codes:
                combo.addItem(L("eng_" + code), code)
            idx = combo.findData(S("engine_" + mode))
            combo.setCurrentIndex(idx if idx >= 0 else 0)
            self.engine_combos[mode] = combo
            form.addRow(L("st_engine_" + mode), combo)

        # Key + nút lấy/kiểm tra cho từng nhà cung cấp
        self.gemini_key = QLineEdit(str(S("gemini_key")))
        self.gemini_key.setEchoMode(QLineEdit.PasswordEchoOnEdit)
        form.addRow(L("st_gemini_key"),
                    self._key_row(self.gemini_key, "gemini"))

        self.groq_key = QLineEdit(str(S("groq_key")))
        self.groq_key.setEchoMode(QLineEdit.PasswordEchoOnEdit)
        form.addRow(L("st_groq_key"), self._key_row(self.groq_key, "groq"))

        self.test_label = QLabel(L("ai_note"))
        self.test_label.setWordWrap(True)
        form.addRow("", self.test_label)

        self.glossary = QTextEdit()
        self.glossary.setPlainText(str(S("tu_dien_ghim")))
        self.glossary.setPlaceholderText("Operation = Vận hành\n"
                                         "Alarm = Cảnh báo")
        self.glossary.setMaximumHeight(90)
        form.addRow(L("st_glossary"), self.glossary)

        tabs.addTab(ai, L("tab_ai"))

        # --- Tab Giới thiệu ---
        about = QWidget()
        about_layout = QVBoxLayout(about)
        info = QLabel(
            f"<h3>{APP_NAME}</h3>"
            f"<p>{L('about_version')} {APP_VERSION}</p>"
            f"<p>{L('about_desc')}</p>"
            f"<p><a href='{GITHUB_URL}'>{GITHUB_URL}</a></p>"
            f"<p>{L('about_license')}</p>")
        info.setWordWrap(True)
        info.setOpenExternalLinks(True)
        about_layout.addWidget(info)
        about_layout.addStretch()
        tabs.addTab(about, L("tab_about"))

        buttons = QDialogButtonBox()
        buttons.addButton(L("btn_save"), QDialogButtonBox.AcceptRole)
        buttons.addButton(L("btn_cancel"), QDialogButtonBox.RejectRole)
        buttons.accepted.connect(self.save)
        buttons.rejected.connect(self.reject)

        layout = QVBoxLayout(self)
        layout.addWidget(tabs)
        layout.addWidget(buttons)

    def _key_row(self, field, provider):
        """Một hàng: ô key + nút 'Lấy key' + nút 'Kiểm tra' cho nhà cung cấp."""
        box = QWidget()
        row = QHBoxLayout(box)
        row.setContentsMargins(0, 0, 0, 0)
        row.addWidget(field, 1)
        page = GROQ_KEY_PAGE if provider == "groq" else GEMINI_KEY_PAGE
        get_key = QPushButton(L("btn_get_key"))
        get_key.clicked.connect(lambda: QDesktopServices.openUrl(QUrl(page)))
        test = QPushButton(L("btn_test_key"))
        test.clicked.connect(lambda: self._test_key(provider))
        row.addWidget(get_key)
        row.addWidget(test)
        return box

    def _test_key(self, provider):
        """Gọi thử engine ở thread nền để cửa sổ không đơ khi chờ mạng."""
        field = self.groq_key if provider == "groq" else self.gemini_key
        key = field.text().strip()
        if not key:
            self.test_label.setText(L("ai_fail") + L("ai_no_key"))
            return
        self.test_label.setText(L("ai_testing"))
        glossary = self.glossary.toPlainText()
        fn = translate_groq if provider == "groq" else translate_gemini

        def work():
            try:
                out = fn(["Hello, this is a test."],
                         key=key, glossary=glossary, timeout=15)
                self._test_done.emit(True, out[0])
            except Exception as e:
                self._test_done.emit(False, str(e)[:160])

        threading.Thread(target=work, daemon=True).start()

    def _on_test_done(self, ok, message):
        if ok:
            self.test_label.setText(L("ai_ok") + " → " + message)
        else:
            self.test_label.setText(L("ai_fail") + message)

    def save(self):
        SETTINGS["ngon_ngu_dich"] = self.lang.currentData()
        SETTINGS["ngon_ngu_giao_dien"] = self.ui_lang.currentData()
        SETTINGS["chu_ky_quet_ms"] = self.interval.value()
        SETTINGS["nguong_thay_doi"] = round(self.threshold.value(), 2)
        SETTINGS["do_tin_cay_ocr"] = round(self.score.value(), 2)
        SETTINGS["ocr_chat_luong"] = self.ocr_quality.currentData()
        for mode, combo in self.engine_combos.items():
            SETTINGS["engine_" + mode] = combo.currentData()
        SETTINGS["gemini_key"] = self.gemini_key.text().strip()
        SETTINGS["groq_key"] = self.groq_key.text().strip()
        SETTINGS["tu_dien_ghim"] = self.glossary.toPlainText().strip()
        set_autostart(self.autostart.isChecked())
        save_settings()
        self.on_saved()
        self.accept()


class Bubble(QWidget):
    """Bong bóng nổi: nhấn = chạy chế độ đang chọn, kéo = di chuyển,
    chuột phải = menu chọn chế độ / cài đặt."""

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
        self.capture_safe = False   # Windows có hỗ trợ loại overlay khỏi ảnh chụp
        self.prev_small = None      # ảnh thu nhỏ của lần quét trước (dò động)
        self.track_prev_half = None  # khung xám nửa trước đó (ước lượng thô)
        self.screen_dirty = True    # màn hình có nội dung mới chưa dịch
        self.need_templates = False  # cần chụp lại ảnh mẫu bám sau khi dịch xong
        self.last_motion = 0.0      # lúc thấy màn hình động gần nhất (giây)
        self.spin_angle = 0

        self.spin_timer = QTimer(self)
        self.spin_timer.timeout.connect(self._spin)
        self.live_timer = QTimer(self)   # vòng chậm: dò đứng yên -> quét dịch
        self.live_timer.timeout.connect(self.live_tick)
        self.track_timer = QTimer(self)  # vòng nhanh: bám ô chữ theo màn hình
        self.track_timer.timeout.connect(self.track_tick)

        self.signals = WorkerSignals()
        self.signals.done.connect(self.on_done)
        self.signals.error.connect(self.on_error)

        self.live_overlay = None
        self.result_overlay = None
        self.selector = None
        self.settings_dialog = None
        self._press_pos = None
        self._dragged = False

    # ----- vẽ bong bóng -----
    def paintEvent(self, _event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        if self.live_on:
            base, light = QColor(30, 140, 74), QColor(110, 220, 150)
        elif self.busy:
            base, light = QColor(206, 100, 16), QColor(255, 184, 100)
        else:
            base, light = QColor(28, 92, 224), QColor(126, 182, 255)

        s = self.SIZE
        p.setPen(Qt.NoPen)

        # Bóng đổ lệch xuống dưới
        p.setBrush(QColor(0, 0, 0, 55))
        p.drawEllipse(5, 7, s - 10, s - 10)

        # Thân cầu: gradient sáng lệch góc trên-trái như quả bóng thật
        grad = QRadialGradient(s * 0.35, s * 0.30, s * 0.75)
        grad.setColorAt(0.0, light)
        grad.setColorAt(1.0, base)
        p.setBrush(QBrush(grad))
        p.drawEllipse(4, 4, s - 10, s - 10)

        # Vệt bóng loáng phía trên
        p.setBrush(QColor(255, 255, 255, 65))
        p.drawEllipse(QRectF(s * 0.24, s * 0.11, s * 0.44, s * 0.26))

        if self.busy:
            p.setPen(QPen(QColor(255, 255, 255), 3))
            p.drawArc(13, 13, s - 28, s - 28, self.spin_angle * 16, 100 * 16)
        else:
            p.setPen(QPen(QColor(255, 255, 255)))
            p.setFont(QFont("Segoe UI", 9, QFont.Bold))
            label = "ON" if self.live_on else L("mode_" + S("che_do"))
            p.drawText(QRectF(4, 4, s - 10, s - 10), Qt.AlignCenter, label)
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
            for key in ("song", "mot_lan", "vung"):
                action = menu.addAction(L("menu_mode_" + key))
                action.setCheckable(True)
                action.setChecked(S("che_do") == key)
                action.triggered.connect(lambda _c, k=key: self.set_mode(k))
            menu.addSeparator()
            menu.addAction(L("menu_settings"), self.open_settings)
            menu.addSeparator()
            menu.addAction(L("menu_quit"), QApplication.instance().quit)
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
                self.activate()
            self._press_pos = None

    def activate(self):
        mode = S("che_do")
        if mode == "song":
            self.toggle_live()
        elif mode == "vung":
            self.region_shot()
        else:
            self.single_shot()

    # ----- chế độ / cài đặt -----
    def set_mode(self, mode):
        if mode != "song" and self.live_on:
            self.stop_live()
        SETTINGS["che_do"] = mode
        save_settings()
        self.update()

    def open_settings(self):
        self.settings_dialog = SettingsDialog(self.apply_settings)
        self.settings_dialog.show()
        self.settings_dialog.raise_()
        self.settings_dialog.activateWindow()

    def apply_settings(self):
        if self.live_timer.isActive():
            self.live_timer.setInterval(int(S("chu_ky_quet_ms")))
        self.screen_dirty = True
        self.update()

    # ----- chế độ dịch sống -----
    def toggle_live(self):
        if self.live_on:
            self.stop_live()
        else:
            self.start_live()

    def start_live(self):
        self.live_on = True
        self.prev_small = None
        self.track_prev_half = None
        self.screen_dirty = True
        self.need_templates = False
        if self.live_overlay is None:
            self.live_overlay = LiveOverlay()
        self.live_overlay.show()
        self.capture_safe = exclude_from_capture(self.live_overlay)
        exclude_from_capture(self)
        # Vòng chậm quyết định khi nào quét dịch. Nếu Windows loại được overlay
        # khỏi ảnh chụp thì bật thêm vòng bám nhanh (chụp liên tục không chớp).
        self.live_timer.start(max(120, int(S("chu_ky_quet_ms")) // 3))
        if self.capture_safe:
            self.track_timer.start(30)   # ~24-30fps, đủ để chữ dính như keo
        self.update()
        self.live_tick()

    def stop_live(self):
        self.live_on = False
        self.live_timer.stop()
        self.track_timer.stop()
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

    def track_tick(self):
        """Vòng nhanh (~24-30fps): giữ mỗi ô dịch dính lấy khối chữ gốc.

        Chụp màn hình liên tục (overlay đã được loại khỏi ảnh chụp nên không
        chớp), dò lại ảnh mẫu của từng ô để bám theo lúc cuộn/kéo cửa sổ, và
        ghi nhận lúc màn hình động để vòng quét biết khi nào đứng yên.
        """
        if not self.live_on or not self.capture_safe:
            return
        try:
            gray = cv2.cvtColor(grab_screen(), cv2.COLOR_BGR2GRAY)
        except Exception:
            return
        small = cv2.resize(gray, (160, 90))
        half = cv2.resize(gray, None, fx=0.5, fy=0.5)
        prev_half = self.track_prev_half
        self.track_prev_half = half
        if self.prev_small is not None:
            dong = (float(np.mean(cv2.absdiff(small, self.prev_small)))
                    >= float(S("nguong_thay_doi")))
            if dong:
                self.last_motion = time.monotonic()
                self.screen_dirty = True   # đứng yên lại sẽ quét bù vùng mới
        self.prev_small = small

        ov = self.live_overlay
        if ov is None or not ov.items:
            return
        if self.need_templates:
            # Vừa dịch xong: chụp ảnh mẫu vùng gốc từng ô ngay khi còn khớp
            capture_templates(ov.items, half, 0.5)
            self.need_templates = False
            return
        if ov.items and ov.items[0].get("_tmpl") is not None:
            song, bam = track_frame(ov.items, half, prev_half, 0.5)
            ov.items = song
            ov.update()
            # Không còn ô nào bám được khi đang động = nội dung đổi hẳn
            # (chuyển tab/app): bỏ bản dịch cũ cho khỏi trơ lại lệch chỗ
            if song and bam == 0 and time.monotonic() - self.last_motion < 0.2:
                ov.set_items([])

    def live_tick(self):
        """Vòng chậm: khi màn hình đã đứng yên một nhịp và còn nội dung mới
        chưa dịch thì chụp và chạy OCR + dịch (đặt lại ảnh mẫu để bám)."""
        if self.busy or not self.live_on:
            return
        if not self.capture_safe:
            # Không loại được overlay khỏi ảnh chụp -> không bám nhanh được,
            # tự dò động ngay tại đây (chụp có ẩn overlay nên chậm hơn)
            img = self._grab_for_ocr()
            small = cv2.resize(cv2.cvtColor(img, cv2.COLOR_BGR2GRAY), (160, 90))
            if self.prev_small is not None and (
                    float(np.mean(cv2.absdiff(small, self.prev_small)))
                    >= float(S("nguong_thay_doi"))):
                self.last_motion = time.monotonic()
                self.screen_dirty = True
                if self.live_overlay is not None:
                    self.live_overlay.set_items([])
            self.prev_small = small

        if not self.screen_dirty:
            return
        # Chờ màn hình đứng yên đủ lâu mới quét (khỏi dịch cảnh đang lướt)
        if time.monotonic() - self.last_motion < 0.35:
            return
        self.screen_dirty = False
        self._set_busy(True)
        img = self._grab_for_ocr()
        threading.Thread(target=run_job, args=(img, self.signals, "song"),
                         daemon=True).start()

    # ----- dịch một lần -----
    def single_shot(self):
        if self.busy:
            return
        exclude_from_capture(self)
        img = self._grab_for_ocr()
        self._set_busy(True)
        threading.Thread(target=run_job, args=(img, self.signals, "mot_lan"),
                         daemon=True).start()

    # ----- dịch vùng chọn -----
    def region_shot(self):
        if self.busy:
            return
        exclude_from_capture(self)
        img = self._grab_for_ocr()
        self.selector = SelectionOverlay()
        self.selector.picked.connect(
            lambda rect: self._region_picked(img, rect))
        self.selector.show()
        self.selector.raise_()
        self.selector.activateWindow()

    def _region_picked(self, img, rect_logical):
        dpr = QApplication.primaryScreen().devicePixelRatio() or 1.0
        h, w = img.shape[:2]
        x0 = max(0, min(w - 1, int(rect_logical.left() * dpr)))
        y0 = max(0, min(h - 1, int(rect_logical.top() * dpr)))
        x1 = max(x0 + 1, min(w, int(rect_logical.right() * dpr)))
        y1 = max(y0 + 1, min(h, int(rect_logical.bottom() * dpr)))
        crop = img[y0:y1, x0:x1].copy()

        self._set_busy(True)
        threading.Thread(target=run_job,
                         args=(crop, self.signals, "vung", (x0, y0)),
                         daemon=True).start()

    # ----- nhận kết quả -----
    def on_done(self, payload):
        items = payload["items"]
        if not payload.get("final", True):
            # Pha 1 (bộ nhớ) ở chế độ sống: cập nhật overlay, vẫn xử lý tiếp
            if self.live_on and self.live_overlay is not None:
                self.live_overlay.set_items(items)
                self.need_templates = True
            return
        self._set_busy(False)
        if payload.get("live"):
            if self.live_on and self.live_overlay is not None:
                self.live_overlay.set_items(items)
                # Bảo vòng bám chụp lại ảnh mẫu vùng gốc từng ô (đang khớp)
                self.need_templates = True
            if payload.get("degraded"):
                # Dịch lỗi (thường do mạng): giữ chế độ sống, đánh dấu để
                # vòng quét sau thử lại thay vì tắt live và bung lỗi
                self.screen_dirty = True
            return
        # Kết quả "dịch một lần" / "dịch vùng"
        dpr = QApplication.primaryScreen().devicePixelRatio()
        has_translation = any(it["dst"] and it["dst"] != it["src"]
                              for it in items)
        if items and not has_translation and payload.get("degraded"):
            panel = L("res_degraded")   # chỉ báo lỗi khi KHÔNG dịch được gì
        else:
            panel = "" if items else L("res_none")
        self.result_overlay = ResultOverlay(items, panel, dpr)
        self.result_overlay.show()
        self.result_overlay.raise_()
        self.result_overlay.activateWindow()

    def on_error(self, message):
        self._set_busy(False)
        self.stop_live()
        self.result_overlay = ResultOverlay(
            [], L("err_translate") + "\n\n" + message, 1.0)
        self.result_overlay.show()
