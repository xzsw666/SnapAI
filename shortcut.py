"""Global hotkey listener for SnapAI.

Listens for Ctrl + Shift + X and invokes a registered callback.
This module has no knowledge of screenshots, GUI, OCR, or clipboard.
"""

import logging

import keyboard

logger = logging.getLogger(__name__)


def register_hotkey(callback) -> None:
    """Register Ctrl + Shift + X as the global hotkey.

    Args:
        callback: A callable with no arguments, invoked when the hotkey
                  is pressed.

    Raises:
        TypeError: If callback is not callable.
    """
    if not callable(callback):
        raise TypeError("callback must be callable")

    keyboard.add_hotkey("ctrl+shift+x", callback)
    logger.info("Registered hotkey: Ctrl + Shift + X")
