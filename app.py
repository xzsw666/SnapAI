"""SnapAI application entry point.

Phase 3 Bugfix B: Replace QTimer polling with Qt Signal/Slot.
"""

import logging
import sys

from PySide6.QtCore import QObject, Signal
from PySide6.QtWidgets import QApplication

from shortcut import register_hotkey
from selector import select_region

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

class _HotkeyBridge(QObject):
    """Bridges keyboard background thread to Qt main thread via Signal."""
    hotkey_pressed = Signal()


_bridge = _HotkeyBridge()
_is_selecting = False


def _on_hotkey() -> None:
    """Called by keyboard library from background thread. Emits Qt signal."""
    _bridge.hotkey_pressed.emit()


def _handle_hotkey() -> None:
    """Handle hotkey press on the Qt main thread (invoked via signal/slot)."""
    global _is_selecting
    if _is_selecting:
        logger.info("Ignoring hotkey: already selecting")
        return

    _is_selecting = True
    logger.info("Opening region selector...")

    result = select_region()
    if result is None:
        logger.info("Selection cancelled")
    else:
        x, y, w, h = result
        logger.info("Region selected: (%d, %d, %d, %d)", x, y, w, h)

    _is_selecting = False


def main() -> None:
    """Run the SnapAI application."""
    logger.info("SnapAI v0.1 Phase 3 Bugfix B starting...")

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
