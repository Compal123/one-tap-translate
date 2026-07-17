# -*- mode: python ; coding: utf-8 -*-
# BẢN GPU: PP-OCR (paddle GPU + CUDA/cuDNN đóng gói đủ) + RapidOCR dự phòng.
# Đóng gói: .venv\Scripts\pyinstaller.exe OneTapTranslate-GPU.spec --noconfirm
# CHỈ chạy trên máy có GPU NVIDIA (driver còn mới); máy khác dùng bản CPU
# (OneTapTranslate.spec). Model PP-OCR tự tải về ~/.paddlex ở lần chạy đầu.
#
# Các bẫy đã gặp khi đóng gói paddle (xem lịch sử git, đừng dẫm lại):
# - paddle.jit.sot làm crash tiến trình quét submodule -> lọc bỏ
# - paddlex check deps qua metadata pip -> phải copy_metadata cả rổ
# - paddlex import pypdfium2 vô điều kiện -> phải giữ pdfium.dll
# - paddlex import sklearn -> cần scipy (không exclude)
# - CUDA/cuDNN nằm ở site-packages\nvidia\*\bin, paddle nạp theo PATH lúc
#   chạy -> phải tự gom DLL + runtime hook rthook_gpu_dlls.py chỉ đường
import glob
import importlib.metadata
import os
import re
import sysconfig

from PyInstaller.utils.hooks import (collect_data_files, collect_submodules,
                                     copy_metadata)

datas = []
hiddenimports = []
for pkg in ("paddleocr", "paddlex", "paddle", "rapidocr"):
    datas += collect_data_files(pkg)
    hiddenimports += collect_submodules(
        pkg, filter=lambda n: not n.startswith("paddle.jit.sot"))

for dist in ("paddlex", "paddleocr", "rapidocr"):
    datas += copy_metadata(dist)
for req in importlib.metadata.requires("paddlex") or []:
    name = re.split(r"[ ;<>=!\[]", req, 1)[0]
    try:
        datas += copy_metadata(name)
    except Exception:
        pass  # gói trong extra không cài -> bỏ qua

# Gom DLL CUDA/cuDNN từ các gói nvidia-* (PyInstaller không tự thấy vì
# paddle nạp chúng động theo PATH lúc chạy)
binaries = []
_sp = sysconfig.get_paths()["purelib"]
for dll in glob.glob(os.path.join(_sp, "nvidia", "*", "bin", "*.dll")):
    binaries.append((dll, os.path.relpath(os.path.dirname(dll), _sp)))

a = Analysis(
    ["main.py"],
    pathex=[],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    runtime_hooks=["rthook_gpu_dlls.py"],
    excludes=["torch", "torchvision", "openvino",
              "matplotlib", "PIL.ImageQt", "tkinter",
              "IPython", "notebook", "pytest"],
    noarchive=False,
)

# --- Lọc bỏ các binary nặng không dùng (chỉ DLL, KHÔNG đụng module Python) ---
_DROP_BIN = (
    "opencv_videoio_ffmpeg",  # cv2 đọc/ghi video - app không dùng (~55MB)
    "opengl32sw",             # OpenGL phần mềm dự phòng (~20MB)
    "qt6quick", "qt6qml",     # QML/Quick - app dùng Widgets (~13MB)
    "qt6pdf",                 # render PDF của Qt (pdfium.dll thì paddlex cần)
    "qt6virtualkeyboard",
    "qt63d", "qt6quick3d", "qt6shadertools",
    "qt6charts", "qt6datavisualization",
    "qt6multimedia", "qt6sensors", "qt6bluetooth", "qt6nfc",
    "qt6sql", "qt6test", "qt6designer", "qt6help", "qt6quickwidgets",
)


def _keep_bin(entry):
    b = os.path.basename(entry[0]).lower()
    return not any(b.startswith(p) or p in b for p in _DROP_BIN)


a.binaries = [e for e in a.binaries if _keep_bin(e)]


# Bỏ thư mục qml + bản dịch của PySide6 trong datas (không dùng QML)
def _keep_data(entry):
    dest = entry[0].replace("\\", "/").lower()
    if "/qml/" in dest or dest.startswith("qml/"):
        return False
    if "pyside6/translations/" in dest:
        return False
    return True


a.datas = [e for e in a.datas if _keep_data(e)]

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="OneTapTranslate",
    debug=False,
    strip=False,
    upx=False,
    console=False,  # app cửa sổ, không hiện console đen
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    name="OneTapTranslate",
)
