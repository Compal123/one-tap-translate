# -*- mode: python ; coding: utf-8 -*-
# Đóng gói: .venv\Scripts\pyinstaller.exe OneTapTranslate.spec --noconfirm
# Kết quả: dist\OneTapTranslate\OneTapTranslate.exe (dạng thư mục, khởi động nhanh)
#
# LƯU Ý: bộ model PP-OCRv5 (~vài chục MB) KHÔNG nhét vào exe - nó tự tải về
# ~/.paddlex ở lần chạy đầu (cần mạng một lần). Máy có sẵn Python 3.12 thì chạy
# từ mã nguồn (setup.bat) cho nhẹ hơn.
#
# TỐI ƯU DUNG LƯỢNG: giữ nguyên các module Python (paddle/paddlex import lúc
# nạp), chỉ LỌC BỎ các DLL nặng KHÔNG BAO GIỜ được nạp trong app này:
#   - cv2 ffmpeg (đọc/ghi file video)   -> app chỉ chụp màn hình
#   - Qt Quick/Qml/Pdf/VirtualKeyboard  -> app dùng Widgets, không dùng QML
#   - opengl32sw (OpenGL phần mềm)       -> overlay vẽ bằng QPainter raster
#   - pdfium.dll (render PDF)            -> không mở PDF
# (mkldnn.dll PHẢI giữ: libpaddle.pyd liên kết cứng, thiếu là không import được.)
import os

from PyInstaller.utils.hooks import collect_data_files, collect_submodules

# paddleocr/paddlex/paddle cần rất nhiều file data (config .yaml, .json...) +
# module nạp động -> gom hết cho PyInstaller khỏi bỏ sót.
datas = []
hiddenimports = []
for pkg in ("paddleocr", "paddlex", "paddle"):
    datas += collect_data_files(pkg)
    # paddle.jit.sot làm crash tiến trình quét submodule của PyInstaller
    # (access violation) -> bỏ qua; nếu paddle import thật thì Analysis
    # tĩnh vẫn tự kéo vào.
    hiddenimports += collect_submodules(
        pkg, filter=lambda n: not n.startswith("paddle.jit.sot"))

a = Analysis(
    ["main.py"],
    pathex=[],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    runtime_hooks=[],
    excludes=["torch", "torchvision", "openvino", "onnxruntime",
              "matplotlib", "PIL.ImageQt", "tkinter",
              "IPython", "notebook", "pytest", "scipy"],
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
