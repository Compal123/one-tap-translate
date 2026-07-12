# -*- coding: utf-8 -*-
"""OCR: đọc chữ từ ảnh màn hình bằng RapidOCR, lọc dòng đáng dịch."""

import re
import threading
import unicodedata

from PySide6.QtCore import QRect

from settings import S

_ocr_engine = None
_ocr_engine_quality = None   # chất lượng của engine đang giữ (để biết khi nào dựng lại)
_ocr_lock = threading.Lock()


def get_ocr():
    """Khởi tạo RapidOCR (lần đầu mất vài giây), dựng lại nếu đổi chất lượng.

    'nhanh' = model PP-OCRv6 small (nhẹ, mặc định).
    'chinh_xac' = model PP-OCRv6 medium (đa ngôn ngữ, đọc chuẩn hơn, nặng ~130MB
    tải lần đầu). Cả hai đều đa ngữ nên không mất tiếng Nhật/Hàn/Nga.
    """
    global _ocr_engine, _ocr_engine_quality
    with _ocr_lock:
        quality = S("ocr_chat_luong")
        if _ocr_engine is None or _ocr_engine_quality != quality:
            from rapidocr import ModelType, RapidOCR
            if quality == "chinh_xac":
                params = {"Det.model_type": ModelType.MEDIUM,
                          "Rec.model_type": ModelType.MEDIUM}
            else:
                params = {}
            _ocr_engine = RapidOCR(params=params)
            _ocr_engine_quality = quality
        return _ocr_engine


def ocr_image(img_bgr):
    """Chạy OCR, trả về list (box, text, score) thống nhất cho rapidocr v2."""
    result = get_ocr()(img_bgr)
    if result is None or result.txts is None:
        return []
    return list(zip(result.boxes, result.txts, result.scores))


# Ký tự CHỈ tiếng Việt mới có. Các dấu dùng chung với Pháp/Bồ/Tây Ban Nha
# (à á â ã è é ê ì í ò ó ô õ ù ú) KHÔNG nằm đây - "Téléphone", "Relógio"
# phải được dịch chứ không bị tưởng nhầm là tiếng Việt.
_VN_RIENG = set(
    "ăđơưýỳạảẹẻịỉọỏụủỵỷẽĩũỹ"
    "ấầẩẫậắằẳẵặếềểễệốồổỗộớờởỡợứừửữự")


def _bo_dau(low):
    """Bỏ dấu Latin (é->e, à->a, đ->d) để soi khung xương âm tiết."""
    return unicodedata.normalize("NFD", low.replace("đ", "d")) \
        .encode("ascii", "ignore").decode()

# Tiếng Việt là ngôn ngữ đơn âm tiết cấu trúc chặt: mỗi từ = phụ âm đầu
# + vần + phụ âm cuối, đều thuộc bộ cố định. OCR hay đánh rơi dấu
# ("Nước" -> "Nuoc") khiến kiểm tra dấu ở trên trượt, app đem tiếng Việt
# đi dịch vòng rồi che chữ méo lên chữ gốc — nên nhận diện thêm dạng mất dấu.
_VN_AM_TIET = re.compile(
    r"^(ngh|ng|nh|ch|gh|gi|kh|ph|qu|th|tr|[bcdghklmnpqrstvx])?"
    r"(uye|uyu|uya|ieu|yeu|uoi|uou|oai|oao|oay|oeo|uay"
    r"|ai|ao|au|ay|eo|eu|ia|ie|iu|oa|oe|oi|oo|ua|ue|ui|uo|uu|uy|ye"
    r"|[aeiouy])"
    r"(ch|ng|nh|[cmnpt])?$")

# Nhiều từ tiếng Anh ngắn cũng vô tình khớp âm tiết Việt ("in the can"),
# nên chỉ kết luận là tiếng Việt khi có ít nhất một từ mang đặc trưng Việt:
# bắt đầu ng/kh/nh, chứa "uo", kết thúc "nh", hoặc vần "iê" mất dấu.
_VN_DAC_TRUNG = re.compile(r"^(ng|kh|nh)|uo|nh$|ie(c|m|n|ng|p|t|u)$")
_VN_TU_QUEN = {  # từ mất dấu hay gặp trên màn hình mà mẫu trên chưa bắt được
    # (tránh từ trùng tiếng Anh thật như "bay", "bat", "chin", "van", "ban")
    "dat", "cai", "muc", "chon", "xoa", "luu", "sua", "loi", "tep",
    "hoac", "neu", "cua", "mot", "hai", "muoi", "quan", "ly", "thong",
    "gio", "phut", "giay", "thang", "hom", "dang", "moi", "cu", "toc",
    "tren", "duoi", "giua", "trai", "cao", "thap", "tat", "trang",
    "thoi", "gian", "dong", "huy", "dung", "xe", "hoi",
}


def _viet_khong_dau(low, co_dau=False):
    """Đoán dòng chữ Latin có phải tiếng Việt bị OCR rơi dấu không.

    low đã được _bo_dau sẵn; co_dau=True nghĩa là dòng gốc có dấu kiểu Tây
    (é/à...) - bản thân dấu là một bằng chứng nếu khung xương từ đều chuẩn
    Việt ("Cà phê" là Việt, còn "Téléphone" trượt khung xương nên vẫn dịch).
    """
    words = re.findall(r"[a-z]+", low)
    if not words:
        return False
    dac_trung = 1 if co_dau else 0
    for w in words:
        if not re.search(r"[aeiouy]", w):
            # Cụm phụ âm trần ("Gh", "Nht", "PLC"): hoặc chữ Việt bị OCR ăn
            # mất nguyên âm, hoặc từ viết tắt - dịch kiểu gì cũng ra rác/y
            # nguyên, nên tính là bằng chứng để bỏ qua luôn
            if len(w) > 4:
                return False
            dac_trung += 1
            continue
        if len(w) > 7 or not _VN_AM_TIET.match(w):
            return False
        if _VN_DAC_TRUNG.search(w) or w in _VN_TU_QUEN:
            dac_trung += 1
    return dac_trung > 0


def should_translate(text):
    """Bỏ qua dòng toàn số/ký hiệu và dòng đã là tiếng Việt (khỏi che, khỏi dịch)."""
    low = text.lower()
    if not any(c.isalpha() for c in low):
        return False
    if S("ngon_ngu_dich") == "vi":
        if any(c in _VN_RIENG for c in low):
            return False
        if any(ord(c) >= 0x0370 for c in low):
            return True  # có chữ Trung/Nhật/Hàn/Nga... chắc chắn phải dịch
        khong_dau = _bo_dau(low)
        if _viet_khong_dau(khong_dau, co_dau=(khong_dau != low)):
            return False
    return True


def extract_items(img_bgr):
    """OCR ảnh -> list item {rect, src, dst=''} (tọa độ pixel vật lý)."""
    items = []
    for box, text, score in ocr_image(img_bgr):
        text = (text or "").strip()
        score = float(score)
        if (not text or score < float(S("do_tin_cay_ocr"))
                or not should_translate(text)):
            continue
        # Mẩu cụt lủn mà điểm không cao thường là rác OCR (chữ Hàn/Nga bị
        # model đọc bừa thành "ō", "Cτy"...) - dịch ra toàn nghĩa bậy nên
        # đòi điểm cao hơn hẳn mới tin
        letters = sum(1 for c in text if c.isalpha())
        if letters <= 2 and score < 0.92:
            continue
        if len(text) <= 3 and score < 0.82:
            continue
        xs = [p[0] for p in box]
        ys = [p[1] for p in box]
        items.append({
            "rect": QRect(int(min(xs)), int(min(ys)),
                          int(max(xs) - min(xs)), int(max(ys) - min(ys))),
            "src": text,
            "dst": "",
        })
    return items
