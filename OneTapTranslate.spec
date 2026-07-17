# -*- mode: python ; coding: utf-8 -*-
# Đóng gói: .venv\Scripts\pyinstaller.exe OneTapTranslate.spec --noconfirm
# Kết quả: dist\OneTapTranslate\OneTapTranslate.exe (dạng thư mục, khởi động nhanh)
#
# BẢN EXE = BẢN CPU, CHỈ RapidOCR (model PP-OCRv6 small đóng gói sẵn, chạy
# offline không cần tải gì thêm). KHÔNG nhét paddle/paddleocr vào exe vì:
#   - paddle bản GPU cần CUDA/cuDNN của đúng máy đích -> đóng gói kiểu gì
#     cũng chết "cudnn64_9.dll not configured" trên máy khác;
#   - paddle bản CPU thì chậm hơn RapidOCR mà nặng thêm ~700MB;
#   - paddlex còn kiểm tra deps qua metadata pip + import sklearn/pypdfium2...
#     kéo theo cả rổ thứ phải vá (đã thử, xem lịch sử git).
# Ai có GPU NVIDIA muốn PP-OCR chính xác hơn -> cài từ mã nguồn (install.bat).
#
# TỐI ƯU DUNG LƯỢNG: chỉ LỌC BỎ các DLL nặng KHÔNG BAO GIỜ được nạp:
#   - cv2 ffmpeg (đọc/ghi file video)   -> app chỉ chụp màn hình
#   - Qt Quick/Qml/Pdf/VirtualKeyboard  -> app dùng Widgets, không dùng QML
#   - opengl32sw (OpenGL phần mềm)       -> overlay vẽ bằng QPainter raster
import os

from PyInstaller.utils.hooks import (collect_data_files, collect_submodules,
                                     copy_metadata)

# rapidocr có model .onnx + config .yaml trong package + module nạp động
# -> gom hết cho PyInstaller khỏi bỏ sót.
datas = []
hiddenimports = []
for pkg in ("rapidocr",):
    datas += collect_data_files(pkg)
    hiddenimports += collect_submodules(pkg)
datas += copy_metadata("rapidocr")

a = Analysis(
    ["main.py"],
    pathex=[],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    runtime_hooks=[],
    # paddle/paddleocr/paddlex CHỦ ĐỘNG loại khỏi exe (xem đầu file);
    # ocr.py tự thấy thiếu gói -> chọn RapidOCR, UI hiện "(chưa cài gói)"
    excludes=["paddle", "paddleocr", "paddlex",
              "torch", "torchvision", "openvino", "scipy", "sklearn",
              "matplotlib", "PIL.ImageQt", "tkinter",
              "IPython", "notebook", "pytest"],
    noarchive=False,
)

# --- Lọc bỏ các binary nặng không dùng (chỉ DLL, KHÔNG đụng module Python) ---
_DROP_BIN = (
    "opencv_videoio_ffmpeg",  # cv2 đọc/ghi video - app không dùng (~55MB)
    "opengl32sw",             # OpenGL phần mềm dự phòng (~20MB)
    "qt6quick", "qt6qml",     # QML/Quick - app dùng Widgets (~13MB)
    "qt6pdf", "pdfium",       # render PDF (~11MB)
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
