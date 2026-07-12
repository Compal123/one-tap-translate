# -*- mode: python ; coding: utf-8 -*-
# Đóng gói: .venv\Scripts\pyinstaller.exe OneTapTranslate.spec --noconfirm
# Kết quả: dist\OneTapTranslate\OneTapTranslate.exe (dạng thư mục, khởi động nhanh)
from PyInstaller.utils.hooks import collect_data_files, collect_submodules

# rapidocr cần model .onnx + file config .yaml nằm trong package
datas = collect_data_files("rapidocr")
hiddenimports = collect_submodules("rapidocr")

a = Analysis(
    ["main.py"],
    pathex=[],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    runtime_hooks=[],
    # rapidocr hỗ trợ nhiều engine nhưng app chỉ dùng onnxruntime
    excludes=["torch", "torchvision", "paddle", "openvino",
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
