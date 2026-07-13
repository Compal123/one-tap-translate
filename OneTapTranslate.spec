# -*- mode: python ; coding: utf-8 -*-
# Đóng gói: .venv\Scripts\pyinstaller.exe OneTapTranslate.spec --noconfirm
# Kết quả: dist\OneTapTranslate\OneTapTranslate.exe (dạng thư mục, khởi động nhanh)
#
# LƯU Ý: gói .exe kéo theo paddlepaddle-gpu + CUDA runtime (cả gói ~vài GB) nên
# vẫn nặng và cần thử lại cẩn thận. Bộ model PP-OCRv5 (~vài chục MB) KHÔNG nhét
# vào exe - nó tự tải về ~/.paddlex ở lần chạy đầu. Nếu máy có sẵn Python thì
# nên chạy từ mã nguồn cho nhẹ.
from PyInstaller.utils.hooks import collect_data_files, collect_submodules

# paddleocr/paddlex/paddle cần rất nhiều file data (config .yaml, .json...) +
# module nạp động -> gom hết cho PyInstaller khỏi bỏ sót.
datas = []
hiddenimports = []
for pkg in ("paddleocr", "paddlex", "paddle"):
    datas += collect_data_files(pkg)
    hiddenimports += collect_submodules(pkg)

a = Analysis(
    ["main.py"],
    pathex=[],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    runtime_hooks=[],
    excludes=["torch", "torchvision", "openvino", "onnxruntime",
              "matplotlib", "PIL.ImageQt", "tkinter"],
    noarchive=False,
)
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
