# -*- coding: utf-8 -*-
"""Pipeline chạy trong thread nền: OCR ảnh rồi dịch, báo kết quả qua Signal."""

import traceback

from PySide6.QtCore import QObject, Signal

from ocr import extract_items
from settings import S
from translate import (_cache, _cached_ok, _ck, _da_thua, engine_ready,
                       translate_cached, translate_engine, translate_vision)


class WorkerSignals(QObject):
    done = Signal(dict)
    error = Signal(str)


def _run_vision(img_bgr, signals, offset):
    """Chế độ 'Gemini nhìn ảnh': OCR + dịch một lần trên cả ảnh (như Google
    Lens). Không dùng PP-OCRv5 cục bộ, không 2 pha. Trả True nếu xong, False nếu
    lỗi để nơi gọi lui về pipeline OCR thường."""
    try:
        items = translate_vision(img_bgr)
    except Exception:
        return False
    if offset != (0, 0):
        for it in items:
            it["rect"].translate(offset[0], offset[1])
    signals.done.emit({"items": items, "final": True,
                       "live": False, "degraded": False})
    return True


def run_job(img_bgr, signals, mode="mot_lan", offset=(0, 0)):
    """Chạy trong thread nền: OCR rồi dịch (có bộ nhớ), 2 pha ở chế độ sống.

    mode = song | mot_lan | vung — quyết định engine dịch (cài đặt riêng
    từng chế độ) và có bật 2 pha (chỉ chế độ live) hay không.
    """
    live = mode == "song"
    engine = S("engine_" + mode)

    # Engine "Gemini nhìn ảnh" (chỉ cho một lần / vùng chọn): đi đường riêng
    if engine == "vision" and not live and engine_ready("vision"):
        if _run_vision(img_bgr, signals, offset):
            return
        # vision lỗi -> lui về OCR thường bên dưới

    try:
        items = extract_items(img_bgr)
        if offset != (0, 0):
            for it in items:
                it["rect"].translate(offset[0], offset[1])
    except Exception:
        signals.error.emit(traceback.format_exc(limit=3))
        return

    # Điền trước phần đã có trong bộ nhớ - vừa là pha 1 của chế độ sống,
    # vừa là phao khi mạng lỗi ở bước dịch bên dưới
    for it in items:
        it["dst"] = _cache.get(_ck(it["src"]), "")
    if live and any(it["dst"] for it in items):
        # Pha 1: dòng nào đã có trong bộ nhớ thì hiện NGAY, khỏi chờ mạng
        signals.done.emit({"items": [dict(it) for it in items],
                           "final": False, "live": True})

    degraded = False
    if items:
        try:
            srcs = [i["src"] for i in items]
            # vision đã xử lý ở trên; tới đây engine chỉ còn google/gemini/groq
            if engine in ("gemini", "groq") and engine_ready(engine):
                dsts = translate_engine(engine, srcs)
            else:
                dsts = translate_cached(srcs)
            for item, dst in zip(items, dsts):
                item["dst"] = dst
        except Exception:
            # Mạng lỗi giữa chừng: giữ kết quả OCR + phần đã cache, thay vì
            # vứt trắng cả lượt
            for it in items:
                it["dst"] = _cache.get(_ck(it["src"]), it["dst"])
        # Còn dòng chữ Hán/Hàn... chưa dịch được (ra y nguyên) -> đánh dấu để
        # chế độ live thử lại vòng sau; dòng đã dịch vẫn giữ nguyên (đã cache),
        # dòng "đã chịu thua" (Latin không dịch nổi) thì thôi, đừng lặp vô tận
        degraded = any(not _cached_ok(it["src"], it["dst"])
                       and _ck(it["src"]) not in _da_thua for it in items)
    signals.done.emit({"items": items, "final": True,
                       "live": live, "degraded": degraded})
