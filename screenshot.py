"""Screen capture module for SnapAI.

Captures screen regions using mss.
Returns in-memory screenshot objects only -- no file I/O.
"""

import logging

import mss
from PySide6.QtGui import QGuiApplication

logger = logging.getLogger(__name__)


def _find_screen_for_logical_point(x: int, y: int):
    """Find the QScreen whose logical geometry contains the point (x, y)."""
    for screen in QGuiApplication.screens():
        geo = screen.geometry()
        if geo.x() <= x < geo.x() + geo.width() and geo.y() <= y < geo.y() + geo.height():
            return screen
    return None


def _logical_to_physical(x: int, y: int, width: int, height: int, screen):
    """Convert Qt logical coordinates to physical pixel coordinates.

    Qt logical virtual desktop -> screen logical geometry -> DPR -> physical pixels
    """
    geo = screen.geometry()
    dpr = screen.devicePixelRatio()

    logical_off_x = x - geo.x()
    logical_off_y = y - geo.y()

    phys_x = round(geo.x() + logical_off_x * dpr)
    phys_y = round(geo.y() + logical_off_y * dpr)
    phys_w = round(width * dpr)
    phys_h = round(height * dpr)

    return phys_x, phys_y, phys_w, phys_h


def capture_region(x: int, y: int, width: int, height: int):
    """Capture a screen region and return an in-memory screenshot object.

    Input coordinates are Qt logical pixels (from selector.py).
    Automatically converts to physical pixels for mss, accounting for DPI scaling.

    Args:
        x: Qt logical x coordinate of the top-left corner.
        y: Qt logical y coordinate of the top-left corner.
        width: Width of the region in Qt logical pixels.
        height: Height of the region in Qt logical pixels.

    Returns:
        An mss.ScreenShot object containing the captured pixels.

    Raises:
        ValueError: If width/height not positive, or region crosses screens.
        RuntimeError: If the point is not on any screen.
    """
    if width <= 0:
        raise ValueError(f"width must be positive, got {width}")
    if height <= 0:
        raise ValueError(f"height must be positive, got {height}")

    target_screen = _find_screen_for_logical_point(x, y)
    if target_screen is None:
        raise RuntimeError(
            f"Logical point ({x}, {y}) is not on any available screen"
        )

    geo = target_screen.geometry()
    screen_right = geo.x() + geo.width()
    screen_bottom = geo.y() + geo.height()
    region_right = x + width
    region_bottom = y + height
    if region_right > screen_right or region_bottom > screen_bottom:
        raise ValueError(
            f"Region ({x}, {y}, {width}, {height}) extends beyond screen "
            f"({geo.x()}, {geo.y()}, {geo.width()}, {geo.height()}). "
            f"Cross-screen selections not supported in Phase 4."
        )

    phys_x, phys_y, phys_w, phys_h = _logical_to_physical(
        x, y, width, height, target_screen
    )

    logger.info(
        "Logical (%d, %d, %d, %d) -> physical (%d, %d, %d, %d) "
        "(screen=%s, DPR=%.1f)",
        x, y, width, height,
        phys_x, phys_y, phys_w, phys_h,
        target_screen.name(),
        target_screen.devicePixelRatio(),
    )

    monitor = {"left": phys_x, "top": phys_y, "width": phys_w, "height": phys_h}

    with mss.MSS() as sct:
        screenshot = sct.grab(monitor)

    logger.info(
        "Captured region -> %dx%d",
        screenshot.width, screenshot.height,
    )
    return screenshot
