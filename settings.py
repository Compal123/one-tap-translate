# -*- coding: utf-8 -*-
"""Cài đặt của app (đọc/ghi cai-dat.json) + bảng chữ giao diện song ngữ."""

import json
import os
import sys

APP_NAME = "One Tap Translate"
APP_VERSION = "1.3.1"
GITHUB_URL = "https://github.com/Compal123/one-tap-translate"

# Khi đóng gói thành exe (PyInstaller), file cài đặt nằm cạnh file exe
if getattr(sys, "frozen", False):
    BASE_DIR = os.path.dirname(sys.executable)
else:
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
SETTINGS_FILE = os.path.join(BASE_DIR, "cai-dat.json")

_DEFAULT_SETTINGS = {
    "che_do": "song",          # song | mot_lan | vung
    "ngon_ngu_dich": "vi",     # dịch sang ngôn ngữ nào
    "ngon_ngu_giao_dien": "vi",  # ngôn ngữ chữ trên giao diện app: vi | en
    "ocr_backend": "auto",     # auto | paddle | rapid (xem ocr.py)
    "do_tin_cay_ocr": 0.50,    # bỏ qua dòng OCR nhận kém tin cậy hơn mức này (lọc rác/icon)
    "so_luong_cpu_ocr": 0,     # số luồng CPU cho OCR; 0 = tự động theo số nhân máy (đỡ nóng CPU)
    "chu_ky_quet_ms": 500,     # bao lâu quét màn hình một lần (mili giây)
    "nguong_thay_doi": 1.5,    # màn hình đổi hơn mức này = "đang cuộn/chuyển"
    # Engine dịch cho từng chế độ: google | gemini | groq (mặc định Groq
    # cho ổn định; google là dự phòng khi engine AI lỗi/thiếu key)
    "engine_song": "groq",     # chế độ dịch live
    "engine_mot_lan": "groq",  # chế độ dịch một lần
    "engine_vung": "groq",     # chế độ dịch vùng chọn
    "gemini_key": "",          # API key Google AI Studio (chỉ lưu trên máy)
    "groq_key": "",            # API key Groq (chỉ lưu trên máy)
    "tu_dien_ghim": "",        # mỗi dòng "gốc = dịch", áp dụng khi dịch AI
    "mau_nen": "#181A26",      # màu nền ô bản dịch (đè lên chữ gốc)
    "mau_chu": "#F0F2FA",      # màu chữ bản dịch
    "phim_tat_bat": True,      # bật phím tắt toàn cục (đổi chế độ / chạy)
    "phim_doi_che_do": "Ctrl+Alt+M",  # phím tắt đổi chế độ (tùy chỉnh được)
    "phim_chay": "Ctrl+Alt+T",        # phím tắt chạy - thay cho nhấn bong bóng
}

SETTINGS = dict(_DEFAULT_SETTINGS)


def S(key):
    return SETTINGS.get(key, _DEFAULT_SETTINGS[key])


def load_settings():
    try:
        with open(SETTINGS_FILE, encoding="utf-8") as f:
            data = json.load(f)
        # Cấu hình cũ (ai_bat + ai_nha_cung_cap, hoặc gemini_bat còn cũ hơn)
        # -> engine riêng từng chế độ
        old_on = data.pop("gemini_bat", None)
        if "ai_bat" in data:
            old_on = data.pop("ai_bat")
        old_provider = data.pop("ai_nha_cung_cap", "groq")
        # Bỏ RapidOCR: cấu hình cũ có "chất lượng OCR" (nhanh/chính xác) giờ vô nghĩa
        data.pop("ocr_chat_luong", None)
        # Bỏ backend Windows OCR (chất lượng kém): cấu hình cũ trót chọn -> auto
        data.pop("windows_ocr_lang", None)
        if data.get("ocr_backend") == "windows":
            data["ocr_backend"] = "auto"
        if old_on is not None and "engine_mot_lan" not in data:
            engine = old_provider if old_on else "google"
            data.setdefault("engine_mot_lan", engine)
            data.setdefault("engine_vung", engine)
            data.setdefault("engine_song", "google")  # live cũ luôn dùng Google
        SETTINGS.update(data)
    except Exception:
        save_settings()


def save_settings():
    try:
        with open(SETTINGS_FILE, "w", encoding="utf-8") as f:
            json.dump(SETTINGS, f, ensure_ascii=False, indent=2)
    except Exception:
        pass


# ---------- Chữ trên giao diện (song ngữ) ----------

_UI_TEXT = {
    "mode_song":      {"vi": "Live",  "en": "Live"},
    "mode_mot_lan":   {"vi": "1 lần", "en": "Once"},
    "mode_vung":      {"vi": "Vùng",  "en": "Area"},
    "menu_mode_song":    {"vi": "Chế độ: Dịch live",
                          "en": "Mode: Live translate"},
    "menu_mode_mot_lan": {"vi": "Chế độ: Dịch một lần",
                          "en": "Mode: Single shot"},
    "menu_mode_vung":    {"vi": "Chế độ: Dịch vùng chọn",
                          "en": "Mode: Select area"},
    "menu_settings": {"vi": "Cài đặt...", "en": "Settings..."},
    "menu_quit":     {"vi": "Thoát",      "en": "Quit"},
    "st_title":     {"vi": "Cài đặt - " + APP_NAME,
                     "en": "Settings - " + APP_NAME},
    "tab_general":  {"vi": "Chung",       "en": "General"},
    "tab_scan":     {"vi": "Quét && OCR", "en": "Scan && OCR"},
    "tab_about":    {"vi": "Giới thiệu",  "en": "About"},
    "st_target":    {"vi": "Dịch sang:",  "en": "Translate to:"},
    "st_ui_lang":   {"vi": "Ngôn ngữ giao diện:",
                     "en": "Interface language:"},
    "st_autostart": {"vi": "Khởi động cùng Windows",
                     "en": "Start with Windows"},
    "st_interval":  {"vi": "Chu kỳ quét (dịch live):",
                     "en": "Scan interval (live mode):"},
    "st_threshold": {"vi": "Độ nhạy thay đổi màn hình:",
                     "en": "Screen-change sensitivity:"},
    "st_score":     {"vi": "Độ tin cậy OCR tối thiểu:",
                     "en": "Minimum OCR confidence:"},
    "st_cpu_threads": {"vi": "Số luồng CPU cho OCR:",
                       "en": "CPU threads for OCR:"},
    "cpu_auto":     {"vi": "Tự động", "en": "Auto"},
    "cpu_hint":     {"vi": "Ít luồng = mát CPU hơn nhưng OCR chậm hơn chút. "
                           "Tự động = chọn mức hợp lý theo số nhân máy bạn. "
                           "Đổi xong lưu là áp dụng ngay.",
                     "en": "Fewer threads = cooler CPU but slightly slower OCR. "
                           "Auto = a sensible level based on your CPU cores. "
                           "Applies right after saving."},
    "st_ocr_backend": {"vi": "Bộ OCR (đọc chữ):", "en": "OCR engine:"},
    "ocr_auto":    {"vi": "Tự chọn theo máy (đề xuất)",
                    "en": "Auto-pick for this PC (recommended)"},
    "ocr_paddle":  {"vi": "PP-OCR — chính xác nhất, cần GPU NVIDIA mới nhanh",
                    "en": "PP-OCR — most accurate, needs an NVIDIA GPU to be fast"},
    "ocr_rapid":   {"vi": "RapidOCR — cân bằng cho máy chỉ có CPU",
                    "en": "RapidOCR — balanced for CPU-only PCs"},
    "ocr_missing": {"vi": " (chưa cài gói)", "en": " (package not installed)"},
    "ocr_note":    {"vi": "Đang dùng: {be}. PP-OCR chính xác nhất nhưng cần "
                          "GPU NVIDIA; máy chỉ có CPU nên dùng RapidOCR.",
                    "en": "Active: {be}. PP-OCR is the most accurate but "
                          "needs an NVIDIA GPU; on CPU-only PCs use RapidOCR."},
    "tab_display": {"vi": "Hiển thị", "en": "Display"},
    "st_bg_color": {"vi": "Màu nền bản dịch:", "en": "Translation background:"},
    "st_fg_color": {"vi": "Màu chữ bản dịch:", "en": "Translation text:"},
    "btn_pick_color": {"vi": "Chọn màu...", "en": "Pick color..."},
    "st_hotkeys":  {"vi": "Bật phím tắt toàn cục", "en": "Enable global hotkeys"},
    "st_hk_mode":  {"vi": "Phím đổi chế độ:", "en": "Switch-mode key:"},
    "st_hk_run":   {"vi": "Phím chạy (thay click):", "en": "Run key (like click):"},
    "hotkey_hint": {"vi": "Bấm vào ô rồi gõ tổ hợp phím mong muốn (nên có Ctrl/Alt/Shift). "
                          "Để trống một ô = tắt phím đó. Nếu phím không ăn thì đã bị app khác chiếm.",
                    "en": "Click a field and press your desired combo (include Ctrl/Alt/Shift). "
                          "Leave a field empty to disable that hotkey. If it doesn't work, another app took it."},
    "btn_save":   {"vi": "Lưu", "en": "Save"},
    "btn_cancel": {"vi": "Hủy", "en": "Cancel"},
    "about_desc": {"vi": "Bong bóng nổi dịch chữ trên màn hình - bản dịch "
                         "đè lên đúng vị trí chữ gốc.",
                   "en": "A floating bubble that translates on-screen text "
                         "- overlaid right on top of the original."},
    "about_version": {"vi": "Phiên bản", "en": "Version"},
    "about_license": {"vi": "Giấy phép MIT", "en": "MIT License"},
    "res_close_hint": {"vi": "Nhấn chuột hoặc Esc để đóng — rê chuột vào ô "
                             "có \"…\" để xem đầy đủ",
                       "en": "Click or press Esc to close — hover a box "
                             "with \"…\" to see the full text"},
    "res_none":     {"vi": "Không tìm thấy chữ cần dịch.",
                     "en": "No text found to translate."},
    "res_degraded": {"vi": "Mạng lỗi khi dịch - chỉ hiển thị được phần đã "
                           "có trong bộ nhớ. Kiểm tra kết nối rồi thử lại.",
                     "en": "Network error while translating - only lines "
                           "already in memory are shown. Check your "
                           "connection and try again."},
    "err_translate": {"vi": "Lỗi khi dịch. Kiểm tra kết nối mạng rồi "
                            "thử lại.",
                      "en": "Translation error. Check your network "
                            "connection and try again."},
    "sel_hint": {"vi": "Kéo chuột khoanh vùng cần dịch — Esc để hủy",
                 "en": "Drag to select the area to translate — Esc to "
                       "cancel"},
    "tab_ai":       {"vi": "Engine dịch", "en": "Engine"},
    "st_engine_song":    {"vi": "Dịch live:",      "en": "Live mode:"},
    "st_engine_mot_lan": {"vi": "Dịch một lần:",   "en": "Single shot:"},
    "st_engine_vung":    {"vi": "Dịch vùng chọn:", "en": "Area select:"},
    "eng_google": {"vi": "Google (miễn phí)", "en": "Google (free)"},
    "eng_gemini": {"vi": "Gemini (cần key)",  "en": "Gemini (needs key)"},
    "eng_groq":   {"vi": "Groq (cần key)",    "en": "Groq (needs key)"},
    "eng_vision": {"vi": "Gemini nhìn ảnh - như Google (cần key, chậm hơn)",
                   "en": "Gemini vision - like Google (needs key, slower)"},
    "st_gemini_key":  {"vi": "Key Gemini:",   "en": "Gemini key:"},
    "st_groq_key":    {"vi": "Key Groq:",     "en": "Groq key:"},
    "btn_get_key":  {"vi": "Lấy key", "en": "Get key"},
    "btn_test_key": {"vi": "Kiểm tra", "en": "Test"},
    "ai_testing":   {"vi": "Đang kiểm tra...", "en": "Testing..."},
    "ai_ok":        {"vi": "✓ Key hoạt động",  "en": "✓ Key works"},
    "ai_fail":      {"vi": "✗ Lỗi: ",          "en": "✗ Error: "},
    "ai_no_key":    {"vi": "chưa nhập key",    "en": "no key entered"},
    "ai_note":      {"vi": "Key chỉ lưu trên máy bạn (cai-dat.json). Groq/"
                           "Gemini ổn định hơn Google nhiều; Google là dự "
                           "phòng khi engine AI lỗi hoặc thiếu key.",
                     "en": "Keys are stored only on this machine "
                           "(cai-dat.json). Groq/Gemini are far more reliable "
                           "than Google; Google is the fallback when the AI "
                           "engine fails or has no key."},
    "st_glossary":  {"vi": "Từ điển ghim\n(mỗi dòng: gốc = dịch):",
                     "en": "Pinned glossary\n(one per line: source = "
                           "target):"},
}


def L(key):
    """Chữ giao diện theo ngôn ngữ đang chọn (mặc định tiếng Việt)."""
    entry = _UI_TEXT.get(key)
    if not entry:
        return key
    return entry.get(S("ngon_ngu_giao_dien")) or entry["vi"]
