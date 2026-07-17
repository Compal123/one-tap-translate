# -*- coding: utf-8 -*-
"""Runtime hook cho bản exe GPU: chỉ đường cho paddle tìm DLL CUDA/cuDNN.

paddle nạp cudnn64_9.dll... bằng LoadLibrary theo PATH; trong exe các DLL
này nằm ở _internal\nvidia\<goi>\bin và _internal\paddle\libs -> phải thêm
vào PATH + add_dll_directory TRƯỚC khi import paddle, không thì nổ
"cudnn64_9.dll is not configured correctly (error code 126)".
"""
import os
import sys

_base = getattr(sys, "_MEIPASS", None)
if _base:
    _dirs = [os.path.join(_base, "paddle", "libs")]
    _nv = os.path.join(_base, "nvidia")
    if os.path.isdir(_nv):
        for _d in os.listdir(_nv):
            _b = os.path.join(_nv, _d, "bin")
            if os.path.isdir(_b):
                _dirs.append(_b)
    for _d in _dirs:
        if os.path.isdir(_d):
            os.add_dll_directory(_d)
            os.environ["PATH"] = _d + os.pathsep + os.environ.get("PATH", "")
