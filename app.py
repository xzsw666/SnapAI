"""SnapAI v0.1 entry point -- coordinates the full capture pipeline.

Capture-First-Select-Second pipeline:

    Ctrl+Shift+X
    -> capture_snapshot()    (immediate mss grab, before any UI)
    -> select_region()       (Win32 polling on frozen snapshot)
    -> crop_from_snapshot()  (no second mss call)
    -> ocr.recognize()
    -> clipboard
"""

import logging
import sys

from PySide6.QtCore import QObject, Signal, Qt
from PySide6.QtGui import QImage, QPixmap
from PySide6.QtWidgets import QApplication, QLabel, QVBoxLayout, QWidget

from shortcut import register_hotkey
from selector import select_region
from screenshot import capture_snapshot, crop_from_snapshot
from ocr import recognize

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)


class _HotkeyBridge(QObject):
    """Bridges keyboard background thread to Qt main thread via Signal."""
    hotkey_pressed = Signal()


_bridge = _HotkeyBridge()
_is_selecting = False
_previews: list[QWidget] = []


def _on_hotkey() -> None:
    """Called by keyboard library from background thread. Emits Qt signal."""
    _bridge.hotkey_pressed.emit()


def _show_preview(screenshot) -> None:
    """Temporary: display captured screenshot for visual verification."""
    logger.info(
        "Creating QImage: %dx%d, rgb len=%d",
        screenshot.width, screenshot.height,
        len(screenshot.rgb),
    )

    # Keep a named reference to prevent GC of the underlying bytes
    rgb_bytes = screenshot.rgb
    bytes_per_line = screenshot.width * 3
    expected_rgb_len = screenshot.width * screenshot.height * 3
    logger.info(
        "QImage input: width=%d height=%d rgb_len=%d "
        "bytes_per_line=%d expected_rgb_len=%d",
        screenshot.width, screenshot.height,
        len(rgb_bytes), bytes_per_line, expected_rgb_len,
    )
    img = QImage(
        rgb_bytes,
        screenshot.width,
        screenshot.height,
        bytes_per_line,
        QImage.Format.Format_RGB888,
    ).copy()
    logger.info(
        "QImage created: width=%d height=%d bytesPerLine=%d sizeInBytes=%d",
        img.width(), img.height(), img.bytesPerLine(), img.sizeInBytes(),
    )

    pixmap = QPixmap.fromImage(img)
    logger.info(
        "QPixmap creation completed: %dx%d",
        pixmap.width(), pixmap.height(),
    )

    preview = QWidget()
    preview.setWindowTitle("SnapAI Preview")
    preview.setWindowFlags(
        Qt.WindowType.WindowStaysOnTopHint | Qt.WindowType.Tool
    )
    layout = QVBoxLayout(preview)
    label = QLabel()
    label.setPixmap(pixmap)
    layout.addWidget(label)
    preview.show()
    QApplication.processEvents()

    _previews.append(preview)
    logger.info("Preview window shown")


def _handle_hotkey() -> None:
    """Handle hotkey press on the Qt main thread (invoked via signal/slot)."""
    global _is_selecting
    if _is_selecting:
        logger.info("Ignoring hotkey: already selecting")
        return

    _is_selecting = True
    logger.info("=" * 60)
    logger.info("SNAP CAPTURE STARTED")
    import time as _time
    _t0 = _time.time()

    # ── Step 1: Capture full virtual desktop snapshot ────────────────
    try:
        snapshot, mapper = capture_snapshot()
    except Exception:
        logger.exception("capture_snapshot failed")
        _is_selecting = False
        return
    _t1 = _time.time()
    logger.info("Timing: snapshot=%.0fms", (_t1 - _t0) * 1000)

    # ── Step 2: Select region from frozen snapshot ───────────────────
    try:
        crop_rect = select_region(mapper, snapshot)
    except Exception:
        logger.exception("select_region failed")
        _is_selecting = False
        return
    _t2 = _time.time()
    logger.info("Timing: selection=%.0fms", (_t2 - _t1) * 1000)

    if crop_rect is None:
        logger.info("Selection cancelled")
        _is_selecting = False
        return

    # ── Step 3: Crop from frozen snapshot ────────────────────────────
    try:
        cropped = crop_from_snapshot(snapshot, crop_rect)
    except Exception:
        logger.exception("crop_from_snapshot failed")
        _is_selecting = False
        return
    _t3 = _time.time()
    logger.info("Timing: crop=%.0fms", (_t3 - _t2) * 1000)

    # ── Step 4: OCR ──────────────────────────────────────────────────
    text = ""
    try:
        text = recognize(cropped)
    except Exception:
        logger.exception("OCR failed")
    _t4 = _time.time()
    logger.info("Timing: OCR=%.0fms", (_t4 - _t3) * 1000)

    # ── Step 5: Clipboard ────────────────────────────────────────────
    if text:
        logger.info("OCR result: %d characters", len(text))
        try:
            clipboard = QApplication.clipboard()
            clipboard.setText(text)
            logger.info("OCR result copied to clipboard: %d characters", len(text))
        except Exception:
            logger.exception("Failed to copy OCR result to clipboard")
    else:
        logger.info("OCR result: <empty>")
    _t5 = _time.time()
    logger.info("Timing: clipboard=%.0fms", (_t5 - _t4) * 1000)

    # ── Step 6: Preview ──────────────────────────────────────────────
    _show_preview(cropped)

    logger.info("Timing: total=%.0fms", (_t5 - _t0) * 1000)
    logger.info("SNAP CAPTURE COMPLETE")
    logger.info("=" * 60)

    _is_selecting = False


def main() -> None:
    """Run the SnapAI application."""
    logger.info("SnapAI v0.1 Phase 4 starting...")

    _app = QApplication(sys.argv)
    _app.setQuitOnLastWindowClosed(False)

    _bridge.hotkey_pressed.connect(_handle_hotkey)
    register_hotkey(_on_hotkey)
    logger.info("Listening for Ctrl + Shift + X. Close the window or press Ctrl+C to exit.")

    try:
        sys.exit(_app.exec())
    except KeyboardInterrupt:
        logger.info("Shutting down SnapAI.")
        sys.exit(0)

if __name__ == "__main__":
    main()
