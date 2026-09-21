# Changelog

All notable changes to SnapAI will be documented in this file.

## [v0.1] — 2026-09-21

### Core Architecture

- **Capture-First-Select-Second pipeline**: Hotkey triggers immediate mss.grab() of entire virtual desktop before any UI, preserving Windows transient menus (right-click, popups, etc.) in the frozen snapshot.
- **Per-screen overlay architecture**: Each QScreen gets its own _ScreenOverlay widget with correct devicePixelRatio, replacing the old single-overlay approach that caused cross-DPR rendering bugs.
- **Win32 API mouse polling**: Selection driven by GetCursorPos / GetAsyncKeyState polling via QTimer instead of Qt mouse events, decoupling visual display from input capture.
- **Four-rectangle dim mask**: Replaced QPainterPath.subtracted() with four explicit illRect() calls to avoid cross-DPR compositor bugs.

### Modules

- **shortcut.py** — Global hotkey listener (keyboard library), background thread
- **pp.py** — Qt main thread orchestrator, signal/slot bridge, timing instrumentation
- **screenshot.py** — capture_snapshot() (full desktop grab), crop_from_snapshot() (zero-second-capture), SnapshotCoordinateMapper (screen ↔ snapshot ↔ logical coordinate conversion)
- **selector.py** — Per-screen overlays with frozen snapshot backgrounds, four-rectangle dim mask, Win32 polling
- **ocr.py** — Windows.Media.Ocr integration via in-memory BMP stream (no file I/O), supports Chinese/English/mixed

### Features

- Global hotkey: Ctrl+Shift+X
- Windows transient menu capture (right-click, context menus preserved)
- Dual-monitor support with different DPRs (2.0 + 1.5 validated)
- ESC cancels selection without exiting the app
- Repeated hotkey ignored during active selection
- OCR result automatically written to system clipboard via QClipboard
- Preview window for visual verification

### Platform

- Windows 10/11 only (Windows.Media.Ocr dependency)
- Python 3.12+
- PySide6 6.11.1, mss 10.2.0, keyboard, winrt-runtime + companion packages
- PyInstaller packaging (SnapAI.spec)

### Known Issues

- Shell flyout UIs (Start Menu, Win+A, calendar) may render above overlay
- OCR accuracy ~75% (Windows native OCR limitations)
- Conda Python environments may lack fi.dll → PyInstaller packaging requires manual DLL inclusion

### Documentation

- README.md — Product-oriented overview with Capture-First architecture
- docs/PRD.md — Full product requirements document
- docs/ARCHITECTURE.md — Architecture Decision Records
- docs/BUILD.md — PyInstaller build guide
- docs/KNOWN_ISSUES.md — Known issues and workarounds
- docs/AI_PRODUCTIVITY_CASE.md — AI-assisted development case study
