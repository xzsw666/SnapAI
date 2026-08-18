"""Screen region selector for SnapAI.

Provides a full-screen overlay that lets the user drag-select a rectangular
region. Returns normalised (x, y, width, height) in screen coordinates.
"""

import logging

from PySide6.QtCore import Qt, QRect, Signal
from PySide6.QtGui import QPainter, QPen, QColor, QGuiApplication
from PySide6.QtWidgets import QApplication, QWidget

logger = logging.getLogger(__name__)


_SELECTOR_ACTIVE = False


class _RegionSelector(QWidget):
    """Transparent overlay widget for mouse-drag region selection."""

    region_selected = Signal(int, int, int, int)

    def __init__(self) -> None:
        super().__init__()

        self._start_x: int = 0
        self._start_y: int = 0
        self._end_x: int = 0
        self._end_y: int = 0
        self._selecting: bool = False
        self._offset_x: int = 0
        self._offset_y: int = 0

        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.Tool
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setCursor(Qt.CursorShape.CrossCursor)
        self.setMouseTracking(True)

        self._setup_screen_geometry()

        self.show()
        self.activateWindow()
        self.raise_()
        QApplication.processEvents()

    def _setup_screen_geometry(self) -> None:
        """Set the widget to cover the entire virtual desktop (all monitors)."""
        geometry = QRect()
        for screen in QGuiApplication.screens():
            geometry = geometry.united(screen.geometry())
        self.setGeometry(geometry)
        self._offset_x = geometry.x()
        self._offset_y = geometry.y()

    def paintEvent(self, event) -> None:  # noqa: N802
        """Draw the selection rectangle overlay."""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        overlay_color = QColor(0, 0, 0, 80)
        painter.fillRect(self.rect(), overlay_color)

        if self._selecting:
            local_x = min(self._start_x, self._end_x) - self._offset_x
            local_y = min(self._start_y, self._end_y) - self._offset_y
            local_w = abs(self._end_x - self._start_x)
            local_h = abs(self._end_y - self._start_y)

            rect = QRect(local_x, local_y, local_w, local_h)

            painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_Clear)
            painter.fillRect(rect, QColor(0, 0, 0, 0))
            painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_SourceOver)

            pen = QPen(QColor(0, 120, 215), 2)
            painter.setPen(pen)
            painter.drawRect(rect)

    def mousePressEvent(self, event) -> None:  # noqa: N802
        """Record the start position of the drag."""
        if event.button() == Qt.MouseButton.LeftButton:
            self._start_x = int(event.globalPosition().x())
            self._start_y = int(event.globalPosition().y())
            self._end_x = self._start_x
            self._end_y = self._start_y
            self._selecting = True
            self.update()

    def mouseMoveEvent(self, event) -> None:  # noqa: N802
        """Update the selection rectangle during drag."""
        if self._selecting:
            self._end_x = int(event.globalPosition().x())
            self._end_y = int(event.globalPosition().y())
            self.update()

    def mouseReleaseEvent(self, event) -> None:  # noqa: N802
        """Finalise the selection on mouse release."""
        if event.button() == Qt.MouseButton.LeftButton and self._selecting:
            self._end_x = int(event.globalPosition().x())
            self._end_y = int(event.globalPosition().y())
            self._selecting = False

            x = min(self._start_x, self._end_x)
            y = min(self._start_y, self._end_y)
            w = abs(self._end_x - self._start_x)
            h = abs(self._end_y - self._start_y)

            self.region_selected.emit(x, y, w, h)
            self.close()

    def keyPressEvent(self, event) -> None:  # noqa: N802
        """Handle ESC key to cancel selection."""
        if event.key() == Qt.Key.Key_Escape:
            self.close()

    def closeEvent(self, event) -> None:  # noqa: N802
        """Clean up when the widget is closed."""
        global _SELECTOR_ACTIVE
        _SELECTOR_ACTIVE = False
        super().closeEvent(event)


def select_region() -> tuple[int, int, int, int] | None:
    """Show a full-screen region selector and return the selected area.

    Returns:
        (x, y, width, height) in screen coordinates if a region was selected,
        or None if the user cancelled (ESC).
    """
    if not QApplication.instance():
        raise RuntimeError("QApplication must be created before calling select_region")

    global _SELECTOR_ACTIVE
    if _SELECTOR_ACTIVE:
        logger.warning("Selector already active, ignoring request")
        return None

    _SELECTOR_ACTIVE = True

    result: tuple[int, int, int, int] | None = None

    def on_selected(x: int, y: int, w: int, h: int) -> None:
        nonlocal result
        result = (x, y, w, h)

    selector = _RegionSelector()
    selector.region_selected.connect(on_selected)

    selector.setFocus()
    QApplication.processEvents()

    while _SELECTOR_ACTIVE:
        QApplication.processEvents()

    return result
