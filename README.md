# One Tap Translate (OTT)

🇻🇳 [Bản tiếng Việt ở đây](README.vi.md)

A floating bubble for Windows that translates text on your screen — games, apps, documents, anything you're looking at — and overlays the translation right on top of the original text.

## Features

- **Live mode** — scans the screen continuously and overlays translations in place. Your mouse clicks through the overlay, so you keep using whatever is underneath normally. Waits until the screen stops changing before translating (nothing wasted while you scroll).
- **Single shot** — click the bubble, get a translated snapshot of the screen, click to dismiss.
- **Region select** — drag a rectangle, translate only that area.
- **Mixed-language screens** — lines are grouped by writing system (Latin / Chinese / Japanese / Korean / Cyrillic...) and each group is translated with its source language set explicitly, so multiple languages on one screen all translate correctly — including traditional Chinese.
- **Settings window** — right-click the bubble: target language (Vietnamese, English, Chinese, Japanese, Korean, Russian), scan interval, sensitivity, **translation background & text color**. Saving applies immediately.
- **Global hotkeys** — by default `Ctrl + Alt + M` switches mode, `Ctrl + Alt + T` runs the current mode (instead of clicking the bubble). Works even while another game/app is focused. **Rebind them freely** or toggle in Settings.
- OCR runs locally on your machine with **PP-OCRv5** (PaddleOCR's detect+recognize pipeline, GPU-accelerated, light & fast); translation uses Google Translate (or Gemini/Groq with a key).

## Download & quick setup

Grab `OneTapTranslate-v1.2.0.zip` from the [latest release](https://github.com/Compal123/one-tap-translate/releases/latest), unzip anywhere, then:

1. Double-click **`setup.bat`** — installs the required libraries (asks whether you have an NVIDIA GPU).
2. Double-click **`run.bat`** to launch. First run auto-downloads the PP-OCRv5 models (~22MB).

Requirements: Windows 10/11 64-bit + **Python 3.12** (`setup.bat` will tell you if it's missing). An NVIDIA GPU makes OCR much faster, but CPU works too.

> The download is small (source only) — the heavy library (PaddlePaddle) and the models are fetched during setup / first run, so they aren't bundled in the zip.

## Install from source

Requires Windows 10/11, **Python 3.12** (PaddlePaddle has no 3.13/3.14 wheels yet),
and preferably an **NVIDIA GPU** (CUDA 12.x) so OCR runs fast.

```
git clone https://github.com/Compal123/one-tap-translate.git
cd one-tap-translate
py -3.12 -m venv .venv

REM 1) PaddlePaddle (pick one for your hardware):
REM    - NVIDIA GPU (recommended):
.venv\Scripts\pip install paddlepaddle-gpu -i https://www.paddlepaddle.org.cn/packages/stable/cu126/
REM    - CPU only (much slower):
REM  .venv\Scripts\pip install paddlepaddle

REM 2) Everything else:
.venv\Scripts\pip install -r requirements.txt
```

On first run PP-OCRv5 downloads its models (~tens of MB) to `%USERPROFILE%\.paddlex` — needs the network once.

## Run

Double-click `run.bat` (or run `.venv\Scripts\python.exe main.py` to see logs).

- **Click the bubble** to trigger the current mode (live toggle / single shot / region select).
- **Right-click** to switch modes, open settings, or quit.
- **Drag** the bubble to move it.
- **Hotkeys**: `Ctrl + Alt + M` switches mode, `Ctrl + Alt + T` runs (instead of clicking the bubble).

## License

MIT
