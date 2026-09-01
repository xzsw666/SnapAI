# SnapAI v0.1

SnapAI is a Windows desktop tool that extracts text from a selected screen region and copies it to the system clipboard.

**Ctrl+Shift+X → 框选 → 截图 → OCR → 自动复制 → Ctrl+V**

## Current Features

- **Global Hotkey** — Ctrl+Shift+X triggers the full pipeline
- **Region Selection** — Drag-select any screen area (supports 4 directions)
- **DPI-Aware Screenshot** — Correctly handles Windows high-DPI scaling
- **Windows Native OCR** — Chinese, English, and mixed text recognition
- **Auto Clipboard** — OCR result is automatically written to system clipboard
- **ESC Cancel** — Cancel selection at any time
- **Repeated Hotkey Ignored** — No double selector during active selection

## Architecture

`
shortcut.py   (keyboard)
    ↓
app.py        (orchestrator)
    ↓
selector.py   (PySide6 overlay)
    ↓
screenshot.py (mss, DPI-aware)
    ↓
ocr.py        (Windows.Media.Ocr)
    ↓
clipboard     (QClipboard)
`

## Project Structure

`
SnapAI/
├── app.py              # Entry point, flow orchestration
├── shortcut.py         # Global hotkey (Ctrl+Shift+X)
├── selector.py         # Screen region selection overlay
├── screenshot.py       # DPI-aware screen capture via mss
├── ocr.py              # Windows native OCR
├── config.py           # Configuration placeholder
├── requirements.txt    # Python dependencies
├── README.md           # This file
├── .env.example        # Environment variable template
├── .gitignore
├── LICENSE
├── docs/
│   └── PRD.md          # Product requirements document
└── tests/
    ├── ocr_probe.py    # OCR verification script
    └── ocr_probe.ps1   # PowerShell OCR probe
`

## Requirements

- Windows 10/11 (Windows.Media.Ocr is Windows-only)
- Python 3.12+
- Dependencies listed in requirements.txt

## Quick Start

1. Create virtual environment:
   `
   python -m venv .venv
   .venv\Scripts\activate
   `

2. Install dependencies:
   `
   pip install -r requirements.txt
   `

3. Run:
   `
   .venv\Scripts\python.exe app.py
   `

4. Press **Ctrl+Shift+X** to select a screen region.

## Current Limitations

- **Windows only** — Windows.Media.Ocr is not available on other platforms
- **Multi-monitor** — Not fully validated; single-monitor works reliably
- **OCR accuracy** — Windows native OCR is ~75% accurate for typical scenarios:
  - l / 1, O / 0 may be confused
  - Extra spaces may appear
  - Small fonts and complex UI reduce accuracy
- **No AI API** — Currently uses Windows native OCR only; no GPT/Claude/Gemini
- **No image saving** — Screenshots exist only in memory during processing

## Privacy

SnapAI uses **Windows native OCR** — all text recognition happens locally on your machine.
No screenshot data is sent to any external service.
Screenshots are not saved to disk.

## Development Status

SnapAI is in **v0.1 — MVP foundation phase**. The core pipeline is stable for single-monitor use.
