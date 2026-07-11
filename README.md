# One Tap Translate (OTT)

🇻🇳 [Bản tiếng Việt ở đây](README.vi.md)

A floating bubble for Windows that translates text on your screen — games, apps, documents, anything you're looking at — and overlays the translation right on top of the original text.

## Features

- **Live mode** — scans the screen continuously and overlays translations in place. Your mouse clicks through the overlay, so you keep using whatever is underneath normally. Waits until the screen stops changing before translating (nothing wasted while you scroll).
- **Single shot** — click the bubble, get a translated snapshot of the screen, click to dismiss.
- **Region select** — drag a rectangle, translate only that area.
- **Translation memory** — every translated line is saved to disk. Text you've seen before appears instantly, no network needed. The longer you use it, the faster it gets.
- **Mixed-language screens** — lines are grouped by writing system (Latin / Chinese / Korean / Cyrillic...) before translation, so multiple languages on one screen all translate correctly.
- **Settings window** — right-click the bubble: target language (Vietnamese, English, Chinese, Japanese, Korean, Russian), scan interval, sensitivity. Saving applies immediately.
- OCR runs locally on your machine (RapidOCR/ONNX); translation uses Google Translate.

## Install

Requires Windows 10/11 and Python 3.10+.

```
git clone https://github.com/Compal123/one-tap-translate.git
cd one-tap-translate
python -m venv .venv
.venv\Scripts\pip install -r requirements.txt
```

## Run

Double-click `run.bat` (or run `.venv\Scripts\python.exe main.py` to see logs).

- **Click the bubble** to trigger the current mode (live toggle / single shot / region select).
- **Right-click** to switch modes, open settings, clear the translation memory, or quit.
- **Drag** the bubble to move it.

## License

MIT
