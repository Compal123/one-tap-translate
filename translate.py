# -*- coding: utf-8 -*-
"""Tầng dịch: Google (deep-translator) + AI (Gemini/Groq) + bộ nhớ trong phiên.

Google là đường chính (nhanh, không cần key); AI là chế độ "dịch kỹ" cho
dịch một lần / vùng chọn - lỗi gì cũng tự lui về Google.
"""

import html
import json
import time

from settings import S

CHUNK_LIMIT = 4000  # giới hạn ký tự mỗi lần gọi Google Dịch

# Nhớ tạm trong phiên (RAM, tắt app là quên): tránh gọi mạng lại
# cho chữ vừa gặp khi cuộn lên xuống ở chế độ dịch live.
_cache = {}

# Dòng Latin mà Google/AI dịch xong vẫn y nguyên (tên riêng, viết tắt...):
# ghi nhận "đã chịu thua" để khỏi hỏi Google lặp lại mãi, nhưng KHÔNG cho
# vào _cache - engine AI vẫn được thử lại (Groq trượt thì Gemini có thể ăn).
_da_thua = set()


def _ck(src):
    """Khóa bộ nhớ dịch: gồm ngôn ngữ đích + chữ gốc đã chuẩn hóa.

    Chuẩn hóa hoa/thường và khoảng trắng để "Operation", "operation ",
    "OPERATION" đều dùng chung một bản dịch - thuật ngữ nhất quán hơn.
    """
    return S("ngon_ngu_dich") + "\x1f" + " ".join(src.lower().split())


def _script_of(text):
    """Đoán hệ chữ của dòng: latin / cjk (Trung) / jp / kr / ru / th.

    Dùng để gom dòng cùng hệ chữ dịch chung một chuyến - màn hình có cả
    tiếng Anh lẫn tiếng Trung thì mỗi thứ đi một đường, Google không đoán nhầm.
    """
    for ch in text:
        o = ord(ch)
        if 0x4E00 <= o <= 0x9FFF or 0x3400 <= o <= 0x4DBF:
            return "cjk"
        if 0x3040 <= o <= 0x30FF:
            return "jp"
        if 0xAC00 <= o <= 0xD7AF:
            return "kr"
        if 0x0400 <= o <= 0x04FF:
            return "ru"
        if 0x0E00 <= o <= 0x0E7F:
            return "th"
    return "latin"


def _cached_ok(src, dst):
    """Phát hiện bản dịch hỏng: 'dịch xong' mà vẫn y nguyên chữ gốc.

    Với chữ Latin, echo cũng tính là hỏng (đừng cache!): Groq từng coi từ
    đơn tiếng Pháp/Bồ là tên riêng rồi trả y nguyên, app cache lại làm mọi
    engine sau đó cùng câm với những ô ấy. Từ thật sự không dịch được sẽ
    vào _da_thua sau khi đã thử lẻ từng dòng."""
    return bool(dst) and dst.strip().lower() != src.strip().lower()


# Google đoán sai ngôn ngữ nguồn với chữ Trung/Nhật... nên nói thẳng
# nguồn của từng nhóm hệ chữ thay vì để "auto"
_SCRIPT_LANG = {"cjk": "zh-CN", "jp": "ja", "kr": "ko",
                "ru": "ru", "th": "th", "latin": "auto"}


def _g_call(translator, text, tries=3):
    """Gọi Google có thử lại + giãn cách: endpoint chùa hay nghẽn khi bị
    dội nhiều lệnh liên tiếp (dịch cả màn hình), trả rỗng/nguyên văn. Thử
    lại vài lần cho bớt trượt trước khi chịu thua."""
    for i in range(tries):
        try:
            out = translator.translate(text)
            if out and out.strip():
                return out
        except Exception:
            pass
        if i < tries - 1:
            time.sleep(0.5 * (i + 1))
    return ""


def translate_lines(lines, source="auto"):
    """Dịch danh sách dòng chữ.

    Trả về (per_line, full_text): per_line là list cùng độ dài với lines
    nếu Google giữ nguyên số dòng, ngược lại per_line = None.
    """
    from deep_translator import GoogleTranslator

    translator = GoogleTranslator(source=source, target=S("ngon_ngu_dich"))

    chunks, current, current_len = [], [], 0
    for line in lines:
        if current and current_len + len(line) + 1 > CHUNK_LIMIT:
            chunks.append(current)
            current, current_len = [], 0
        current.append(line)
        current_len += len(line) + 1
    if current:
        chunks.append(current)

    out_lines = []
    aligned = True
    full_parts = []
    for chunk in chunks:
        translated = html.unescape(_g_call(translator, "\n".join(chunk)))
        full_parts.append(translated)
        parts = [p.strip() for p in translated.split("\n")]
        if len(parts) == len(chunk):
            out_lines.extend(parts)
        else:
            aligned = False
    return (out_lines if aligned and len(out_lines) == len(lines) else None,
            "\n".join(full_parts))


def _translate_group(lines, source="auto"):
    """Dịch một nhóm dòng cùng hệ chữ, luôn trả list khớp từng dòng."""
    from deep_translator import GoogleTranslator
    translator = GoogleTranslator(source=source, target=S("ngon_ngu_dich"))

    per_line, _full = translate_lines(lines, source)
    if per_line is None:
        # Google gộp/tách dòng -> dịch từng dòng một cho chắc
        per_line = [html.unescape(_g_call(translator, ln)) or ln for ln in lines]

    # Dòng nào dịch thất bại (không phải Latin mà ra y nguyên) -> thử lại lẻ
    for i, (src, dst) in enumerate(zip(lines, per_line)):
        if not _cached_ok(src, dst):
            retry = html.unescape(_g_call(translator, src))
            if retry:
                per_line[i] = retry
    return per_line


def translate_cached(lines):
    """Dịch qua bộ nhớ: chỉ gọi mạng cho dòng chưa gặp.

    Dòng mới được gom theo hệ chữ (Anh đi với Anh, Trung đi với Trung...)
    để mỗi nhóm được Google nhận diện ngôn ngữ chính xác.
    """
    missing = {}   # hệ chữ -> list dòng chưa có trong nhớ tạm (không trùng)
    seen = set()
    for ln in lines:
        key = _ck(ln)
        if key not in _cache and key not in _da_thua and key not in seen:
            seen.add(key)
            missing.setdefault(_script_of(ln), []).append(ln)
    for script, group in missing.items():
        source = _SCRIPT_LANG.get(script, "auto")
        for src, dst in zip(group, _translate_group(group, source)):
            # Không cache bản dịch hỏng (chữ Hán ra y nguyên) -> lần quét
            # sau còn thử lại thay vì kẹt chữ gốc mãi
            if _cached_ok(src, dst):
                _cache[_ck(src)] = dst
            elif script == "latin" and dst.strip().lower() == src.strip().lower():
                # Dịch cả cụm lẫn thử lẻ vẫn y nguyên: từ Google chịu thua
                # (tên riêng, viết tắt) - nhớ lại để khỏi hỏi hoài
                _da_thua.add(_ck(src))
    return [_cache.get(_ck(ln), ln) for ln in lines]


# ---------- Dịch AI (Gemini / Groq) ----------

# Gemini bản Lite: tối ưu tốc độ (dịch màn hình cần nhanh hơn "thông minh
# sâu"); alias -latest để Google tự trỏ về đời model mới nhất
GEMINI_MODEL = "gemini-flash-lite-latest"
GEMINI_URL = ("https://generativelanguage.googleapis.com/v1beta/models/"
              + GEMINI_MODEL + ":generateContent")
GEMINI_KEY_PAGE = "https://aistudio.google.com/apikey"

# Groq: LLM mở chạy trên chip suy luận chuyên dụng, phản hồi rất nhanh
GROQ_MODEL = "llama-3.3-70b-versatile"
GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"
GROQ_KEY_PAGE = "https://console.groq.com/keys"

# Gemini vision: nhìn thẳng vào ảnh, OCR + dịch cùng lúc (như Google Lens)
VISION_URL = ("https://generativelanguage.googleapis.com/v1beta/models/"
              + GEMINI_MODEL + ":generateContent")

# Tên ngôn ngữ viết bằng tiếng Anh trong prompt cho model hiểu chắc chắn
_LANG_NAMES = {"vi": "Vietnamese", "en": "English",
               "zh-CN": "Simplified Chinese", "ja": "Japanese",
               "ko": "Korean", "ru": "Russian"}


def engine_ready(engine):
    """Engine có sẵn sàng không: Google luôn được; các engine dùng Gemini
    (gemini/vision) cần key Gemini; Groq cần key Groq."""
    if engine == "groq":
        return bool(str(S("groq_key")).strip())
    if engine in ("gemini", "vision"):
        return bool(str(S("gemini_key")).strip())
    return True  # google


def _glossary_pairs(raw=None):
    """Từ điển ghim 'gốc = dịch' mỗi dòng -> list (gốc, dịch), bỏ dòng hỏng."""
    text = str(S("tu_dien_ghim") if raw is None else raw)
    pairs = []
    for line in text.splitlines():
        if "=" in line:
            src, dst = line.split("=", 1)
            if src.strip() and dst.strip():
                pairs.append((src.strip(), dst.strip()))
    return pairs


def _ai_prompt(lines, glossary=None):
    """Prompt chung cho mọi AI: đánh số từng dòng + thuật ngữ ghim bắt buộc."""
    target = _LANG_NAMES.get(S("ngon_ngu_dich"), S("ngon_ngu_dich"))
    rules = ""
    pairs = _glossary_pairs(glossary)
    if pairs:
        rules = ("\nAlways use these exact term translations:\n"
                 + "\n".join("- %s = %s" % p for p in pairs))
    numbered = "\n".join("%d|%s" % (i + 1, ln) for i, ln in enumerate(lines))
    # Đừng dặn "keep proper names unchanged": Groq vin vào đó coi từ đơn
    # tiếng Pháp/Bồ ("Mesa", "Computador") là tên riêng rồi trả y nguyên
    return ("The numbered lines below were read from a computer screen "
            "(OCR). They may be in different languages.\n"
            "Translate EVERY line into %s, even single words.%s\n"
            "Reply in the same numbered format 'N|translation', one line "
            "each, no extra text. Keep numbers and codes unchanged."
            "\n\n%s" % (target, rules, numbered))


def _match_lines(lines, text):
    """Ghép phản hồi 'N|bản dịch' về đúng dòng gốc, cache phần nhận được.

    KHÔNG raise khi thiếu dòng — trả list cùng độ dài lines, dòng thiếu/
    dịch hỏng = None để nơi gọi tự bù (Google). Nhờ vậy một phản hồi thiếu
    vài dòng vẫn giữ được phần đã dịch thay vì vứt cả cụm về dự phòng.
    """
    out = {}
    for line in text.splitlines():
        num, sep, dst = line.strip().partition("|")
        dst = dst.strip()
        if sep and num.strip().isdigit():
            i = int(num.strip())
            # chỉ nhận bản dịch thật (chữ Hán/Hàn... mà ra y nguyên = hỏng)
            if 1 <= i <= len(lines) and _cached_ok(lines[i - 1], dst):
                _cache[_ck(lines[i - 1])] = dst
                out[i] = dst
    return [out.get(i + 1) for i in range(len(lines))]


def translate_gemini(lines, key=None, glossary=None, timeout=25):
    """Dịch bằng Gemini. Lỗi gì cũng raise - nơi gọi tự lui về Google."""
    import requests

    params = {"key": (key if key is not None
                      else str(S("gemini_key"))).strip()}
    body = {"contents": [{"parts": [{"text": _ai_prompt(lines, glossary)}]}],
            "generationConfig": {
                "temperature": 0.2,
                # Dịch không cần "suy nghĩ sâu" - tắt bớt cho phản hồi nhanh
                "thinkingConfig": {"thinkingLevel": "low"}}}
    resp = requests.post(GEMINI_URL, params=params, json=body,
                         timeout=timeout)
    if resp.status_code == 400:
        # Model đời khác không nhận thinkingLevel -> bỏ tham số, thử lại
        body["generationConfig"].pop("thinkingConfig", None)
        resp = requests.post(GEMINI_URL, params=params, json=body,
                             timeout=timeout)
    resp.raise_for_status()
    parts = resp.json()["candidates"][0]["content"]["parts"]
    text = "".join(p.get("text", "") for p in parts if not p.get("thought"))
    return _match_lines(lines, text)


def translate_groq(lines, key=None, glossary=None, timeout=25):
    """Dịch bằng Groq (API kiểu OpenAI). Lỗi gì cũng raise như Gemini."""
    import requests

    resp = requests.post(
        GROQ_URL,
        headers={"Authorization": "Bearer " + (
            key if key is not None else str(S("groq_key"))).strip()},
        json={"model": GROQ_MODEL,
              "messages": [{"role": "user",
                            "content": _ai_prompt(lines, glossary)}],
              "temperature": 0.2},
        timeout=timeout)
    resp.raise_for_status()
    return _match_lines(lines, resp.json()["choices"][0]["message"]["content"])


def _strip_fence(text):
    """Bỏ rào ```json ... ``` nếu model bọc kết quả trong khối code."""
    t = text.strip()
    if t.startswith("```"):
        t = t.split("\n", 1)[-1] if "\n" in t else t[3:]
        if t.rstrip().endswith("```"):
            t = t.rstrip()[:-3]
    return t.strip()


def _json_salvage(text):
    """Đọc JSON array; nếu phản hồi bị cắt cụt giữa chừng (hết chỗ token
    trên màn dày chữ) thì cứu các phần tử còn nguyên vẹn thay vì vứt hết."""
    t = _strip_fence(text)
    try:
        return json.loads(t)
    except ValueError:
        cut = t.rfind("}")
        if cut < 0:
            raise
        return json.loads(t[:cut + 1] + "]")


def translate_vision(img_bgr, key=None, glossary=None, timeout=60):
    """OCR + dịch cùng lúc bằng Gemini nhìn thẳng vào ảnh (như Google Lens).

    Bỏ qua RapidOCR - đọc dấu tiếng Việt và chữ Hán chuẩn hơn hẳn. Trả list
    item {rect, src, dst} với rect theo pixel của ảnh truyền vào. Lỗi -> raise.
    """
    import base64

    import cv2
    import requests
    from PySide6.QtCore import QRect

    # Box Gemini trả về là tọa độ chuẩn hóa 0-1000 nên độc lập độ phân giải:
    # màn to (4K/nhiều màn) thì co bớt cho nhanh, nhưng giữ đủ lớn để chữ
    # nhỏ trong game không bị mờ. Box vẫn map về pixel gốc.
    h, w = img_bgr.shape[:2]
    send = img_bgr
    scale = 1920 / max(h, w)
    if scale < 1:
        send = cv2.resize(img_bgr, (int(w * scale), int(h * scale)),
                          interpolation=cv2.INTER_AREA)
    ok, buf = cv2.imencode(".png", send)
    if not ok:
        raise ValueError("Không mã hóa được ảnh")
    b64 = base64.b64encode(buf.tobytes()).decode()

    target = _LANG_NAMES.get(S("ngon_ngu_dich"), S("ngon_ngu_dich"))
    rules = ""
    pairs = _glossary_pairs(glossary)
    if pairs:
        rules = ("\nAlways use these exact term translations: "
                 + "; ".join("%s = %s" % p for p in pairs))
    # Đừng thêm kiểu "omit pieces already in Vietnamese" vào prompt: thử rồi,
    # model hăng máu bỏ luôn cả cột chữ Hán. Ô đã là tiếng Việt cứ để model
    # trả ra (dst = y nguyên) rồi code lọc ở dưới.
    prompt = ("Read ALL text in this screenshot and translate each piece "
              "into %s. Include EVERY text block: every table cell, label, "
              "button and short word - do not skip or merge any. "
              "Return ONLY a JSON array; each element "
              '{"src":"original text","dst":"%s translation",'
              '"box":[ymin,xmin,ymax,xmax]} with box normalized to 0-1000. '
              "No markdown, no explanation.%s" % (target, target, rules))

    body = {"contents": [{"parts": [
                {"text": prompt},
                {"inline_data": {"mime_type": "image/png", "data": b64}}]}],
            "generationConfig": {"temperature": 0.1,
                                 # Trần đầu ra của flash-lite: màn dày chữ
                                 # (bảng biểu, trang web) JSON rất dài, chặn
                                 # thấp hơn là bị cắt cụt mất chữ
                                 "maxOutputTokens": 65536,
                                 # Tắt hẳn "suy nghĩ" cho nhanh + khỏi bị cắt
                                 # cụt kết quả (dịch ảnh không cần lập luận sâu)
                                 "thinkingConfig": {"thinkingBudget": 0}}}
    params = {"key": (key if key is not None
                      else str(S("gemini_key"))).strip()}
    resp = requests.post(VISION_URL, params=params, json=body, timeout=timeout)
    if resp.status_code == 400:
        # Model đời khác không nhận tham số nào đó -> bỏ hết, thử lại mộc
        body["generationConfig"].pop("thinkingConfig", None)
        body["generationConfig"].pop("maxOutputTokens", None)
        resp = requests.post(VISION_URL, params=params, json=body,
                             timeout=timeout)
    resp.raise_for_status()
    parts = resp.json()["candidates"][0]["content"]["parts"]
    text = "".join(p.get("text", "") for p in parts if not p.get("thought"))
    data = _json_salvage(text)

    items = []
    for it in data:
        src = str(it.get("src", "")).strip()
        dst = str(it.get("dst", "")).strip()
        box = it.get("box") or []
        if not src or len(box) != 4:
            continue
        if not dst or dst.lower() == src.lower():
            # Đã là ngôn ngữ đích / model lặp y nguyên (pinyin...) -> đừng
            # dán đè chính nó lên chữ gốc cho rối màn hình
            continue
        ymin, xmin, ymax, xmax = box
        x = int(min(xmin, xmax) / 1000 * w)
        y = int(min(ymin, ymax) / 1000 * h)
        bw = max(1, int(abs(xmax - xmin) / 1000 * w))
        bh = max(1, int(abs(ymax - ymin) / 1000 * h))
        items.append({"rect": QRect(x, y, bw, bh), "src": src, "dst": dst})
        if dst and _cached_ok(src, dst):
            _cache[_ck(src)] = dst
    return items


def translate_engine(engine, lines):
    """Dịch tận dụng bộ nhớ: chỉ gọi engine cho dòng CHƯA có trong cache,
    dòng nào engine bỏ sót/dịch hỏng thì Google bù ngay dòng đó.

    Nhờ vậy dòng đã dịch được giữ nguyên (không gọi lại, ổn định), và một
    lần engine trượt không xóa kết quả cũ - chỉ những dòng còn thiếu mới
    phải dịch lại. Luôn trả list cùng độ dài lines.
    """
    if engine in ("groq", "gemini"):
        fn = translate_groq if engine == "groq" else translate_gemini
        missing = [ln for ln in dict.fromkeys(lines) if _ck(ln) not in _cache]
        if missing:
            try:
                fn(missing)  # cache phần dịch được (không raise vì thiếu dòng)
            except Exception:
                pass         # lỗi mạng cả cụm -> để Google bù bên dưới
    # Dòng nào vẫn chưa có trong cache -> Google (cũng có retry riêng)
    rest = [ln for ln in dict.fromkeys(lines) if _ck(ln) not in _cache]
    if rest:
        translate_cached(rest)
    return [_cache.get(_ck(ln), ln) for ln in lines]
