# -*- coding: utf-8 -*-
"""Kiểm tra bộ lọc tiếng Việt (có dấu lẫn bị OCR rơi dấu) — chạy offline."""

import sys

sys.stdout.reconfigure(encoding="utf-8")

from ocr import should_translate

# Các dòng PHẢI bỏ qua (là tiếng Việt — có dấu hoặc bị OCR đánh rơi dấu)
BO_QUA = [
    "Nước lạnh",            # tiếng Việt còn dấu
    "Nuoc lanh",            # rơi dấu: chứa "uo", kết thúc "nh"
    "Cai dat he thong",     # cài đặt hệ thống
    "Khong co ket noi",     # không có kết nối
    "Nguoi dung",           # người dùng
    "Quan ly thoi gian",    # quản lý thời gian
    "Dieu khien",           # điều khiển
    "Nhiet do cao",         # nhiệt độ cao
    "Khoi dong lai may",    # khởi động lại máy
    "Trang thai hoat dong", # trạng thái hoạt động
    "Luu va thoat",         # lưu và thoát
    "Chon tep",             # chọn tệp
    "123 456",              # toàn số — không dịch
    "---",                  # toàn ký hiệu — không dịch
    "Cà phê",               # tiếng Việt chỉ mang dấu chung với tiếng Tây
    "Tiéng Trung",          # OCR đọc lệch dấu nhưng vẫn là tiếng Việt
    "Đồng hò",              # rơi dấu một nửa
    "Gh",                   # OCR ăn mất nguyên âm ("Ghế")
    "Ting Nht",             # "Tiếng Nhật" bị ăn dấu lẫn nguyên âm
    "PLC",                  # viết tắt trần — dịch chỉ ra y nguyên/rác
]

# Các dòng PHẢI dịch (tiếng nước ngoài thật)
PHAI_DICH = [
    "Hello world",
    "The quick brown fox",
    "Machine error: replace the battery",
    "Operation",
    "Alarm Setting",
    "ON OFF Run Stop",
    "in the can",           # toàn từ khớp âm tiết Việt nhưng không có từ đặc trưng
    "you may go",
    "Loading bay 3",
    "System Config",
    "温度设定",              # tiếng Trung
    "Привет мир",           # tiếng Nga
    "エラー発生",            # tiếng Nhật
    "Temperature 温度",      # dòng trộn Anh + Trung
    "Téléphone",            # tiếng Pháp — dấu é KHÔNG phải cứ có là tiếng Việt
    "Relógio",              # tiếng Bồ
    "Garrafa de água",      # tiếng Bồ nhiều từ
    "Café",                 # dấu Tây nhưng khung xương không phải âm tiết Việt
    "Chaise", "Voiture",    # tiếng Pháp không dấu
    "PLC Status",           # viết tắt đi kèm từ thật thì vẫn dịch
]

loi = []
for text in BO_QUA:
    if should_translate(text):
        loi.append(f"PHAI bo qua nhung lai dich: {text!r}")
for text in PHAI_DICH:
    if not should_translate(text):
        loi.append(f"PHAI dich nhung lai bo qua: {text!r}")

if loi:
    print("\n".join(loi))
    sys.exit(1)
print(f"OK - {len(BO_QUA)} dong Viet duoc bo qua, {len(PHAI_DICH)} dong ngoai van dich.")
