# -*- coding: utf-8 -*-
"""OCR: đọc chữ từ ảnh màn hình, lọc dòng đáng dịch.

Hai backend, chọn trong Cài đặt ("auto" = tự dò theo máy, xem _resolve):
- paddle : PP-OCRv5 (paddleocr) - chính xác nhất, cần GPU NVIDIA mới nhanh
- rapid  : RapidOCR (ONNX, model PP-OCRv6 small) - cho máy chỉ có CPU

(Đã thử Windows OCR có sẵn của Windows 10/11: rất nhanh (~0.3s) nhưng chất
lượng đọc kém hẳn + mỗi engine chỉ biết một ngôn ngữ -> bỏ.)
"""

import importlib.util
import os
import re
import sys
import threading
import unicodedata

from PySide6.QtCore import QRect

from settings import S

# Đặt TRƯỚC khi import paddle/paddleocr: bỏ bước "kiểm tra kết nối tới nơi chứa
# model" của PaddleX (model đã tải sẵn trong ~/.paddlex nên không cần hỏi mạng).
os.environ.setdefault("PADDLE_PDX_DISABLE_MODEL_SOURCE_CHECK", "True")

BACKENDS = ("paddle", "rapid")

_backend = None                   # backend đã chốt (init_backend / fallback)
_engine = None                    # engine của backend đó (dựng lười)
_ocr_lock = threading.Lock()      # chỉ khoá lúc dựng engine
_predict_lock = threading.Lock()  # 1 engine: chạy predict tuần tự cho an toàn


def _installed(mod):
    try:
        return importlib.util.find_spec(mod) is not None
    except Exception:
        return False


def available_backends():
    """{tên backend: máy này có gói để chạy không} - cho UI cài đặt + auto."""
    return {
        "paddle": _installed("paddle") and _installed("paddleocr"),
        "rapid": _installed("rapidocr") or _installed("rapidocr_onnxruntime"),
    }


def _paddle_has_gpu():
    try:
        import paddle
        return (paddle.device.is_compiled_with_cuda()
                and paddle.device.cuda.device_count() > 0)
    except Exception:
        return False


def _resolve(choice, avail):
    """Chốt backend: người dùng chọn đích danh thì chiều, còn 'auto' thì
    có GPU -> paddle; không GPU -> RapidOCR; đường cùng mới paddle CPU (lag)."""
    if choice in BACKENDS and avail.get(choice):
        return choice
    order = []
    if avail["paddle"] and _paddle_has_gpu():
        order.append("paddle")
    if avail["rapid"]:
        order.append("rapid")
    if avail["paddle"]:
        order.append("paddle")
    if not order:
        raise RuntimeError(
            "Không có backend OCR nào - cài 'rapidocr' (kèm onnxruntime) "
            "hoặc 'paddleocr' rồi mở lại app.")
    return order[0]


def init_backend():
    """Chốt backend theo cài đặt. PHẢI gọi ở MAIN THREAD (sau load_settings);
    đổi lựa chọn trong Cài đặt thì gọi lại (nút Lưu chạy trên main thread).

    Lý do phải main thread: nếu paddle được import LẦN ĐẦU trong thread nền,
    paddle không bật đúng chế độ dynamic graph cho cả tiến trình -> nổ
    "int(Tensor) is not supported in static graph mode" ở MỌI lần predict
    chạy trong thread. Import ở đây + disable_static() một lần là chuẩn.
    """
    global _backend, _engine
    avail = available_backends()
    with _ocr_lock:
        _backend = _resolve(str(S("ocr_backend") or "auto"), avail)
        _engine = None
        # paddle nằm trong chuỗi dự phòng của mọi lựa chọn -> hễ máy có cài
        # là import ngay tại đây (main thread), kể cả đang chọn backend khác
        if avail["paddle"]:
            try:
                import paddle
                paddle.disable_static()
            except Exception:
                pass
    return _backend


def active_backend():
    """Backend đang dùng thật (sau auto/fallback) - cho UI hiển thị."""
    return _backend


def _build_engine(name):
    if name == "paddle":
        # Model 'mobile' nhẹ + nhanh (~2s/màn hình trên GPU), đọc Hán/Latin/
        # Nhật/Hàn chung một model. Tắt các bước phụ (xoay tài liệu, nắn cong,
        # xoay dòng) vì ảnh màn hình không cần, cho nhanh.
        import paddle
        paddle.disable_static()
        from paddleocr import PaddleOCR
        return PaddleOCR(
            text_detection_model_name="PP-OCRv5_mobile_det",
            text_recognition_model_name="PP-OCRv5_mobile_rec",
            use_doc_orientation_classify=False,
            use_doc_unwarping=False,
            use_textline_orientation=False,
            # Tắt oneDNN: PaddlePaddle 3.3.x chạy CPU qua oneDNN bị lỗi
            # "ConvertPirAttribute2RuntimeAttribute not support" -> tắt đi
            # để dùng kernel CPU thường (GPU không ảnh hưởng).
            enable_mkldnn=False,
            # Giới hạn số luồng CPU: mặc định Paddle gồng hết luồng ->
            # CPU nhảy 70%+ mỗi lần OCR. Số luồng lấy từ cài đặt (0 = tự
            # động theo số nhân máy); GPU thì tham số này không ảnh hưởng.
            cpu_threads=cpu_threads_ocr(),
        )
    if name == "rapid":
        try:
            # Mặc định của rapidocr mới (>=3.9) đã là model PP-OCRv6 small -
            # cứ để nó tự chọn model tốt nhất nó có
            from rapidocr import RapidOCR
            return RapidOCR()
        except ImportError:
            from rapidocr_onnxruntime import RapidOCR  # gói cũ trước v2
            return RapidOCR()
    raise ValueError("backend lạ: %r" % name)


def cpu_threads_ocr():
    """Số luồng CPU dùng cho OCR.

    Lấy từ cài đặt 'so_luong_cpu_ocr'; 0 = tự động = ~1/4 số luồng máy
    (kẹp trong [2, 8]). Giới hạn luồng để mỗi lần OCR không "gồng" hết CPU
    (mặc định Paddle ăn tới 70%+); GPU thì tham số này không ảnh hưởng.
    """
    n = int(S("so_luong_cpu_ocr") or 0)
    if n > 0:
        return n
    total = os.cpu_count() or 4
    return max(2, min(8, round(total / 4)))


def reset_engine():
    """Xoá engine đã dựng để lần OCR kế tiếp dựng lại (vd sau khi đổi số luồng CPU)."""
    global _engine
    with _ocr_lock:
        _engine = None


def get_ocr():
    """Dựng engine của backend đã chốt (lần đầu có thể phải tải model).

    Dựng lỗi (thiếu gói, thiếu language pack, GPU trục trặc...) thì tự lui
    xuống backend kế tiếp còn khả dụng thay vì chết hẳn.
    """
    global _backend, _engine
    with _ocr_lock:
        if _engine is not None:
            return _engine
        avail = available_backends()
        chain = [_backend or _resolve("auto", avail)]
        for name in ("rapid", "paddle"):
            if avail.get(name) and name not in chain:
                chain.append(name)
        errs = []
        for name in chain:
            try:
                _engine = _build_engine(name)
                _backend = name
                return _engine
            except Exception:
                import traceback
                err = "--- %s ---\n%s" % (name, traceback.format_exc())
                errs.append(err)
                # In ra stderr để soi được cả khi đã fallback thành công
                # (bản console / chạy từ terminal mới thấy)
                print("OCR backend loi:\n" + err, file=sys.stderr)
        raise RuntimeError("OCR: không dựng được backend nào %s\n%s"
                           % (chain, "\n".join(errs)))


def ocr_image(img_bgr):
    """Chạy OCR, trả list (box, text, score) thống nhất cho mọi backend.

    box = 4 điểm polygon [[x,y],...]; text = chữ đọc được; score = điểm tin
    cậy nhận dạng thật của từng dòng (chữ rõ ~0.9+, rác/icon ~0.1-0.3).
    Ảnh truyền vào là numpy BGR (như cv2).
    """
    eng = get_ocr()
    with _predict_lock:
        if _backend == "rapid":
            return _predict_rapid(eng, img_bgr)
        return _predict_paddle(eng, img_bgr)


def _predict_paddle(pipe, img_bgr):
    items = []
    for res in pipe.predict(img_bgr):
        j = res.json
        data = j.get("res", j) if isinstance(j, dict) else {}
        texts = data.get("rec_texts", [])
        polys = data.get("rec_polys") or data.get("dt_polys") or []
        scores = data.get("rec_scores", [])
        for i, text in enumerate(texts):
            if not text or i >= len(polys):
                continue
            score = scores[i] if i < len(scores) else 1.0
            items.append((polys[i], text, float(score)))
    return items


def _predict_rapid(eng, img_bgr):
    out = eng(img_bgr)
    items = []
    if out is None:
        return items
    if isinstance(out, tuple):  # rapidocr_onnxruntime cũ: (result, elapse)
        for box, text, score in (out[0] or []):
            items.append((box, text, float(score)))
        return items
    boxes = getattr(out, "boxes", None)  # rapidocr >= 2: RapidOCROutput
    txts = getattr(out, "txts", None) or []
    scores = getattr(out, "scores", None) or []
    if boxes is None:
        return items
    for i, text in enumerate(txts):
        if i >= len(boxes):
            break
        score = scores[i] if i < len(scores) else 1.0
        items.append((boxes[i], text, float(score)))
    return items


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

# Chỉ kết luận là tiếng Việt khi có ít nhất một từ mang đặc trưng Việt:
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
