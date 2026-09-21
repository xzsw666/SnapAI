"""Screen capture module for SnapAI.

Captures screen regions using mss.
Returns in-memory screenshot objects only -- no file I/O.
"""

import logging
import ctypes
import ctypes.wintypes

import mss
from PySide6.QtGui import QGuiApplication

logger = logging.getLogger(__name__)


# ── Win32 API helpers ────────────────────────────────────────────────────────

_user32 = ctypes.windll.user32


class _POINT(ctypes.Structure):
    _fields_ = [("x", ctypes.c_long), ("y", ctypes.c_long)]


_user32.GetCursorPos.argtypes = [ctypes.POINTER(_POINT)]
_user32.GetCursorPos.restype = ctypes.c_bool
_user32.GetAsyncKeyState.argtypes = [ctypes.c_int]
_user32.GetAsyncKeyState.restype = ctypes.c_short

_VK_LBUTTON = 0x01
_VK_ESCAPE = 0x1B


def get_cursor_pos():
    """Get current cursor position in Windows physical screen coordinates."""
    pt = _POINT()
    if _user32.GetCursorPos(ctypes.byref(pt)):
        return pt.x, pt.y
    return None, None


def is_key_down(vk_code):
    """Check if a virtual key is currently pressed."""
    return (_user32.GetAsyncKeyState(vk_code) & 0x8000) != 0


def is_left_button_down():
    return is_key_down(_VK_LBUTTON)


def is_escape_pressed():
    return is_key_down(_VK_ESCAPE)


# ── SnapshotCoordinateMapper ─────────────────────────────────────────────────

class SnapshotCoordinateMapper:
    """Maps between Windows physical screen, snapshot pixel, and Qt logical coords."""

    def __init__(self, snapshot):
        self._snapshot = snapshot
        self._screens = QGuiApplication.screens()

    @property
    def snapshot_left(self) -> int:
        return self._snapshot.left

    @property
    def snapshot_top(self) -> int:
        return self._snapshot.top

    def screen_to_snapshot(self, x: int, y: int):
        """Windows physical screen coords → snapshot pixel coords (for crop)."""
        return (x - self._snapshot.left, y - self._snapshot.top)

    def screen_to_logical(self, px: int, py: int):
        """Windows physical screen coords → Qt logical coords (for overlay drawing)."""
        for screen in self._screens:
            geo = screen.geometry()
            dpr = screen.devicePixelRatio()
            pl, pt = geo.x(), geo.y()
            pr = pl + int(geo.width() * dpr)
            pb = pt + int(geo.height() * dpr)
            if pl <= px < pr and pt <= py < pb:
                lx = geo.x() + (px - pl) / dpr
                ly = geo.y() + (py - pt) / dpr
                return (lx, ly), screen
        return (float(px), float(py)), None

    def rect_to_snapshot(self, start_x: int, start_y: int, end_x: int, end_y: int):
        """Screen rect → normalized snapshot crop rect in snapshot pixels."""
        sx1, sy1 = self.screen_to_snapshot(start_x, start_y)
        sx2, sy2 = self.screen_to_snapshot(end_x, end_y)
        return (
            int(min(sx1, sx2)), int(min(sy1, sy2)),
            int(abs(sx2 - sx1)), int(abs(sy2 - sy1)),
        )

    def find_screen_for_physical_point(self, x: int, y: int):
        """Find QScreen containing a physical screen point."""
        for screen in self._screens:
            geo = screen.geometry()
            dpr = screen.devicePixelRatio()
            pl, pt = geo.x(), geo.y()
            pr = pl + int(geo.width() * dpr)
            pb = pt + int(geo.height() * dpr)
            if pl <= x < pr and pt <= y < pb:
                return screen
        return None


# ── capture_snapshot ─────────────────────────────────────────────────────────

def capture_snapshot():
    """Capture full virtual desktop immediately — must be called before any UI.

    Returns:
        (mss.ScreenShot, SnapshotCoordinateMapper)
    """
    with mss.MSS() as sct:
        snapshot = sct.grab(sct.monitors[0])

    mapper = SnapshotCoordinateMapper(snapshot)
    logger.info(
        "Snapshot captured: left=%d top=%d width=%d height=%d rgb_len=%d",
        snapshot.left, snapshot.top,
        snapshot.width, snapshot.height,
        len(snapshot.rgb),
    )
    return snapshot, mapper


# ── crop_from_snapshot ───────────────────────────────────────────────────────

def crop_from_snapshot(snapshot, crop_rect):
    """Crop a region from existing snapshot — no second mss call.

    Args:
        snapshot: mss.ScreenShot from capture_snapshot().
        crop_rect: (x, y, width, height) in snapshot pixel coords.

    Returns:
        _ScreenShotProxy with .rgb, .width, .height for ocr.recognize().
    """
    from PySide6.QtGui import QImage

    crop_x, crop_y, crop_w, crop_h = crop_rect
    if crop_w <= 0 or crop_h <= 0:
        raise ValueError(f"Invalid crop rect: ({crop_x}, {crop_y}, {crop_w}, {crop_h})")

    rgb = snapshot.rgb
    full = QImage(
        rgb, snapshot.width, snapshot.height,
        snapshot.width * 3, QImage.Format.Format_RGB888,
    ).copy()

    cropped = full.copy(crop_x, crop_y, crop_w, crop_h)
    bpl = cropped.bytesPerLine()
    expected_bpl = cropped.width() * 3

    if bpl == expected_bpl:
        rgb_bytes = bytes(cropped.bits())[:crop_w * crop_h * 3]
    else:
        rows = []
        bits = bytes(cropped.bits())
        for row in range(cropped.height()):
            start = row * bpl
            rows.append(bits[start:start + expected_bpl])
        rgb_bytes = b"".join(rows)

    logger.info(
        "Crop from snapshot: rect=(%d,%d,%d,%d) size=%dx%d rgb_len=%d",
        crop_x, crop_y, crop_w, crop_h,
        cropped.width(), cropped.height(), len(rgb_bytes),
    )
    return _ScreenShotProxy(rgb_bytes, cropped.width(), cropped.height())


class _ScreenShotProxy:
    """Lightweight duck-typed replacement for mss.ScreenShot for ocr.recognize()."""
    __slots__ = ("rgb", "width", "height")

    def __init__(self, rgb: bytes, width: int, height: int):
        self.rgb = rgb
        self.width = width
        self.height = height


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
