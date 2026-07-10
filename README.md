# Screen Translator (Dịch Màn Hình)

🇻🇳 [Bản tiếng Việt ở đây](README.vi.md)

A floating bubble for Windows that translates **everything on your screen** — overlaying translations right on top of the original text. Works with any application: browsers, image-based PDFs, games, industrial/HMI software, video subtitles...

Think of Chrome's "always translate", but for your **entire screen**, not just web pages.

## Why?

Built by a Vietnamese speaker who reads no other language. Chrome translates web pages, but nothing translates the rest of the screen — desktop apps, machine HMIs, PDFs that are just images. Windows' built-in OCR doesn't even support Vietnamese. This app fills that gap, and can target any language Google Translate supports.

## Features

- **Live mode** — scans the screen continuously, overlays translations in place, and your mouse **clicks through** the overlay so you keep using the app underneath normally. Waits until the screen stops changing (no wasted work while you scroll).
- **Single shot** — click the bubble, get a translated snapshot, click to dismiss.
- **Region select** — drag a rectangle, translate only that area.
- **Translation memory** — every translated line is cached to disk (`bo-nho-dich.json`). Previously seen text appears instantly, offline, forever. The longer you use it, the faster it gets.
- **Settings window** — right-click the bubble → Settings: target language, scan interval, sensitivity. Applies immediately.
- OCR runs **locally** (RapidOCR/ONNX — no Windows OCR language packs needed); translation uses Google Translate (free web endpoint).

## Install

Requires Windows 10/11 and Python 3.10+.

```
git clone https://github.com/Compal123/dich-man-hinh.git
cd dich-man-hinh
python -m venv .venv
.venv\Scripts\pip install -r requirements.txt
```

## Run

Double-click `run.bat` (or run `.venv\Scripts\python.exe main.py` to see logs).

- **Click the bubble** to trigger the current mode (live toggle / single shot / region select).
- **Right-click** to switch modes, open settings, clear the translation memory, or quit.
- **Drag** the bubble to move it.

## How it works

Capture screen (mss) → detect if the screen is still changing (frame diff, skip if scrolling) → OCR (RapidOCR) → skip lines already in the target language → translate uncached lines (Google) → paint overlay boxes at the original text positions. The overlay windows exclude themselves from screen capture (`WDA_EXCLUDEFROMCAPTURE`) so the scanner never re-reads its own output.

## Roadmap (ideas & PRs welcome)

1. OCR only the changed screen regions instead of the full frame (lower latency).
2. Optional offline translation model (no network dependency).
3. "Deep translate" button for important paragraphs (LLM, context/terminology-aware).
4. Multi-monitor support.
5. Android version (bubble + MediaProjection).

## License

MIT
