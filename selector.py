"""Screen region selector for SnapAI.

Provides full-screen overlays (one per monitor) that let the user drag-select
a rectangular region. Uses Capture-First-Select-Second: displays frozen snapshot
as background so transient menus remain visible, drives selection via
Win32 API polling.

Returns crop coordinates in snapshot physical pixels, or None on ESC.
"""

import logging

from PySide6.QtCore import Qt, QRect, QTimer
from PySide6.QtGui import QPainter, QPen, QColor, QGuiApplication, QImage, QPixmap
from PySide6.QtWidgets import QApplication, QWidget

from screenshot import (
    get_cursor_pos, is_left_button_down, is_escape_pressed,
)

logger = logging.getLogger(__name__)
_SELECTOR_ACTIVE = False


class _ScreenOverlay(QWidget):
    """Full-screen overlay for a single QScreen showing frozen snapshot."""

    def __init__(self, screen, selector, background=None):
        super().__init__()
        self._screen = screen
        self._selector = selector
        self._background = background  # QPixmap with devicePixelRatio set, or None

        geo = screen.geometry()
        self.setGeometry(geo)

        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setCursor(Qt.CursorShape.CrossCursor)

        self.show()
        self.raise_()

    def paintEvent(self, event):
        """Draw frozen snapshot background, dim layer, and selection rect."""
        p = QPainter(self)

        # Layer 1: frozen snapshot background
        if self._background is not None:
            p.drawPixmap(0, 0, self._background)

        full = self.rect()

        sel = self._selector
        if not sel._dragging:
            p.fillRect(full, QColor(0, 0, 0, 80))
            return

        (slx, sly), _ = sel._mapper.screen_to_logical(
            sel._phys_start_x, sel._phys_start_y,
        )
        (clx, cly), _ = sel._mapper.screen_to_logical(
            sel._phys_curr_x, sel._phys_curr_y,
        )

        geo = self._screen.geometry()
        lx = int(min(slx, clx)) - geo.x()
        ly = int(min(sly, cly)) - geo.y()
        lw = int(abs(clx - slx))
        lh = int(abs(cly - sly))

        if lw <= 0 or lh <= 0:
            p.fillRect(full, QColor(0, 0, 0, 80))
            return

        selection_rect = QRect(lx, ly, lw, lh)
        if not full.intersects(selection_rect):
            p.fillRect(full, QColor(0, 0, 0, 80))
            return

        selection_rect = selection_rect.normalized()
        dim_color = QColor(0, 0, 0, 80)

        top_rect = QRect(full.left(), full.top(),
                         full.width(), selection_rect.top() - full.top())
        bottom_rect = QRect(full.left(), selection_rect.bottom() + 1,
                            full.width(), full.bottom() - selection_rect.bottom())
        left_rect = QRect(full.left(), selection_rect.top(),
                          selection_rect.left() - full.left(), selection_rect.height())
        right_rect = QRect(selection_rect.right() + 1, selection_rect.top(),
                           full.right() - selection_rect.right(), selection_rect.height())

        logger.debug(
            "PAINT: widget=%s sel=%s top=%s bottom=%s left=%s right=%s",
            full, selection_rect, top_rect, bottom_rect, left_rect, right_rect,
        )

        if top_rect.height() > 0:
            p.fillRect(top_rect, dim_color)
        if bottom_rect.height() > 0:
            p.fillRect(bottom_rect, dim_color)
        if left_rect.width() > 0:
            p.fillRect(left_rect, dim_color)
        if right_rect.width() > 0:
            p.fillRect(right_rect, dim_color)

        p.setPen(QPen(QColor(0, 120, 215), 2))
        p.drawRect(selection_rect)

    def closeEvent(self, event):
        self._selector._on_overlay_closed(self)
        super().closeEvent(event)


class _RegionSelector:
    """Coordinates per-screen overlays and Win32 API polling."""

    def __init__(self, mapper, snapshot):
        self._mapper = mapper

        self._phys_start_x: int = 0
        self._phys_start_y: int = 0
        self._phys_curr_x: int = 0
        self._phys_curr_y: int = 0
        self._dragging: bool = False
        self._cancelled: bool = False
        self._was_down: bool = False

        screens = QGuiApplication.screens()
        self._overlays: list[_ScreenOverlay] = []
        self._open_overlays: set[int] = set()

        # Build per-screen background pixmaps from frozen snapshot
        if snapshot is not None:
            rgb_bytes = snapshot.rgb
            full_img = QImage(
                rgb_bytes, snapshot.width, snapshot.height,
                snapshot.width * 3, QImage.Format.Format_RGB888,
            ).copy()
            logger.info("Built full snapshot QImage: %dx%d", full_img.width(), full_img.height())
        else:
            full_img = None
            logger.info("No snapshot provided, overlays will be dim-only")

        for screen in screens:
            geo = screen.geometry()
            dpr = screen.devicePixelRatio()

            background = None
            if full_img is not None:
                sn_x = geo.x() - snapshot.left
                sn_y = geo.y() - snapshot.top
                sn_w = int(geo.width() * dpr)
                sn_h = int(geo.height() * dpr)

                # Clamp to snapshot bounds
                sn_x = max(0, min(sn_x, snapshot.width))
                sn_y = max(0, min(sn_y, snapshot.height))
                sn_w = min(sn_w, snapshot.width - sn_x)
                sn_h = min(sn_h, snapshot.height - sn_y)

                crop = full_img.copy(sn_x, sn_y, sn_w, sn_h)
                pixmap = QPixmap.fromImage(crop)
                pixmap.setDevicePixelRatio(dpr)
                background = pixmap

                logger.info(
                    "Screen %s bg: sn=(%d,%d,%d,%d) pix=%dx%d DPR=%.1f",
                    screen.name(), sn_x, sn_y, sn_w, sn_h,
                    pixmap.width(), pixmap.height(), dpr,
                )

            overlay = _ScreenOverlay(screen, self, background)
            self._overlays.append(overlay)
            self._open_overlays.add(id(overlay))

        QApplication.processEvents()

    def _poll(self):
        """Called via QTimer. Polls Win32 API for mouse and key state."""
        px, py = get_cursor_pos()
        if px is None:
            return

        prev_x, prev_y = self._phys_curr_x, self._phys_curr_y
        self._phys_curr_x = px
        self._phys_curr_y = py

        if is_escape_pressed():
            self._cancelled = True
            self._close_all()
            return

        down = is_left_button_down()
        if down and not self._was_down and not self._dragging:
            self._phys_start_x, self._phys_start_y = px, py
            self._dragging = True
            self._update_all()
        elif down and self._dragging:
            if px != prev_x or py != prev_y:
                logger.debug(
                    "DIAG drag: phys=(%d,%d) -> (%d,%d)",
                    self._phys_start_x, self._phys_start_y, px, py,
                )
            self._update_all()
        elif not down and self._dragging:
            self._phys_curr_x, self._phys_curr_y = px, py
            self._close_all()
            return

        self._was_down = down

    def _update_all(self):
        for o in self._overlays:
            o.repaint()

    def _close_all(self):
        for o in self._overlays:
            o.close()

    def _on_overlay_closed(self, overlay):
        oid = id(overlay)
        if oid in self._open_overlays:
            self._open_overlays.discard(oid)
        if not self._open_overlays:
            global _SELECTOR_ACTIVE
            _SELECTOR_ACTIVE = False


def select_region(mapper, snapshot=None):
    """Show overlays (with frozen snapshot background) and let user select.

    Args:
        mapper: SnapshotCoordinateMapper from capture_snapshot().
        snapshot: mss.ScreenShot from capture_snapshot(). If provided,
                  rendered as background behind the dim overlay so that
                  transient menus remain visible during selection.

    Returns:
        (crop_x, crop_y, crop_w, crop_h) in snapshot physical pixels, or None.
    """
    if not QApplication.instance():
        raise RuntimeError("QApplication must be created before calling select_region")

    global _SELECTOR_ACTIVE
    if _SELECTOR_ACTIVE:
        logger.warning("Selector already active, ignoring request")
        return None

    _SELECTOR_ACTIVE = True

    selector = _RegionSelector(mapper, snapshot)

    timer = QTimer()
    timer.timeout.connect(selector._poll)
    timer.start(5)

    while _SELECTOR_ACTIVE:
        QApplication.processEvents()

    timer.stop()

    if selector._cancelled:
        logger.info("Selection cancelled (ESC)")
        return None

    crop_rect = selector._mapper.rect_to_snapshot(
        selector._phys_start_x, selector._phys_start_y,
        selector._phys_curr_x, selector._phys_curr_y,
    )

    crop_x, crop_y, crop_w, crop_h = crop_rect
    logger.info(
        "Selection complete: physical=(%d,%d -> %d,%d) crop=(%d,%d,%d,%d)",
        selector._phys_start_x, selector._phys_start_y,
        selector._phys_curr_x, selector._phys_curr_y,
        crop_x, crop_y, crop_w, crop_h,
    )

    if crop_w <= 0 or crop_h <= 0:
        logger.warning("Selection too small, returning None")
        return None

    return crop_rect
