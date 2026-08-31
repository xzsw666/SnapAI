"""SnapAI application entry point.

Phase 4: Integrate screenshot module.
"""

import logging
import sys

from PySide6.QtCore import QObject, Signal, Qt
from PySide6.QtGui import QImage, QPixmap
from PySide6.QtWidgets import QApplication, QLabel, QVBoxLayout, QWidget

from shortcut import register_hotkey
from selector import select_region
from screenshot import capture_region
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
    logger.info("Opening region selector...")

    result = select_region()
    _is_selecting = False

    if result is None:
        logger.info("Selection cancelled")
        return

    x, y, w, h = result
    logger.info("Region selected: (%d, %d, %d, %d)", x, y, w, h)

    logger.info("Capture started: x=%d, y=%d, width=%d, height=%d", x, y, w, h)
    try:
        screenshot = capture_region(x, y, w, h)
        logger.info(
            "Capture completed: logical region=(%d, %d, %d, %d), "
            "screenshot size=%dx%d, rgb len=%d",
            x, y, w, h,
            screenshot.width, screenshot.height,
            len(screenshot.rgb),
        )
    except Exception:
        logger.exception("capture_region failed")
        return
    _show_preview(screenshot)
    try:
        text = recognize(screenshot)
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
    except Exception:
        logger.exception("OCR failed")


def main() -> None:
    """Run the SnapAI application."""
    logger.info("SnapAI v0.1 Phase 4 starting...")

    _app = QApplication(sys.argv)

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
