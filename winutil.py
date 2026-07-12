# -*- coding: utf-8 -*-
"""Tiện ích Windows: khởi động cùng Windows, chụp màn hình,
loại overlay khỏi ảnh chụp."""

import ctypes
import os
import sys
import winreg

import numpy as np
from mss import mss

from settings import BASE_DIR

_RUN_KEY = r"Software\Microsoft\Windows\CurrentVersion\Run"
_RUN_NAME = "OneTapTranslate"


def _autostart_command():
    """Lệnh Windows sẽ chạy lúc đăng nhập: bản exe hoặc pythonw + main.py."""
    if getattr(sys, "frozen", False):
        return '"%s"' % sys.executable
    pyw = os.path.join(BASE_DIR, ".venv", "Scripts", "pythonw.exe")
    if not os.path.exists(pyw):
        pyw = sys.executable
    return '"%s" "%s"' % (pyw, os.path.join(BASE_DIR, "main.py"))


def autostart_enabled():
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, _RUN_KEY) as key:
            winreg.QueryValueEx(key, _RUN_NAME)
        return True
    except OSError:
        return False


def set_autostart(enable):
    """Bật/tắt khởi động cùng Windows (chỉ sửa registry của người dùng)."""
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, _RUN_KEY, 0,
                            winreg.KEY_SET_VALUE) as key:
            if enable:
                winreg.SetValueEx(key, _RUN_NAME, 0, winreg.REG_SZ,
                                  _autostart_command())
            else:
                try:
                    winreg.DeleteValue(key, _RUN_NAME)
                except FileNotFoundError:
                    pass
        return True
    except OSError:
        return False


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


_sct = None   # giữ lại một phiên mss dùng chung (tạo mới mỗi lần chụp rất tốn:
              # ~40ms; tái dùng còn ~5-10ms - đủ cho vòng bám tốc độ cao)


def grab_screen():
    """Chụp màn hình chính, trả về ảnh BGR. Chỉ gọi từ luồng giao diện."""
    global _sct
    try:
        if _sct is None:
            _sct = mss()
        shot = _sct.grab(_sct.monitors[1])
    except Exception:
        # Phiên cũ hỏng (đổi độ phân giải/khóa máy...) -> dựng lại một lần
        try:
            _sct = mss()
            shot = _sct.grab(_sct.monitors[1])
        except Exception:
            _sct = None
            raise
    return np.asarray(shot)[:, :, :3].copy()
