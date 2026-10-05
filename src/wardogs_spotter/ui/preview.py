"""The capture in a window of its own: the frames, the HUD as it is drawn over
the game, and what the reader is doing. For checking the capture and the
reader, and for running without the game on saved screenshots."""

import time
from collections.abc import Callable

import numpy as np
from PySide6.QtCore import QPointF, QRectF, QSize, Qt, QTimer, Signal
from PySide6.QtGui import QColor, QFont, QFontMetricsF, QImage, QKeyEvent, QPainter, QPaintEvent
from PySide6.QtWidgets import QWidget

from wardogs_spotter.capture.frames import FrameBuffer, RateMeter
from wardogs_spotter.ui.hud import HudPainter
from wardogs_spotter.ui.images import to_qimage
from wardogs_spotter.ui.model import HudModel

POLL_MS = 8  # how often a new frame is looked for
IDLE_REDRAW = 0.25  # seconds; redraw the stats even when no frame arrives
IDLE_SIZE = QSize(960, 540)  # until the first frame arrives


class PreviewWindow(QWidget):
    """Shows the newest frame with the HUD over it. S asks for a screenshot;
    Q, Esc or closing the window ends the program."""

    screenshot_requested = Signal()

    def __init__(
        self,
        frames: FrameBuffer,
        hud: HudPainter,
        model: Callable[[], HudModel],
        stats: Callable[[], list[str]],
        hud_scale: float = 1.0,
    ) -> None:
        super().__init__()
        self.setWindowTitle("Wardogs Spotter")
        self.resize(IDLE_SIZE)
        self._frames = frames
        self._hud = hud
        self._model = model
        self._stats = stats
        self._hud_scale = hud_scale
        self._frame: np.ndarray | None = None  # kept alive: the image shares its pixels
        self._image: QImage | None = None
        self._count = 0
        self._painted_at = 0.0
        self._displayed = RateMeter()
        self._timer = QTimer(self)
        self._timer.setInterval(POLL_MS)
        self._timer.timeout.connect(self._refresh)

    def start(self) -> None:
        self._timer.start()
        self.show()

    def _refresh(self) -> None:
        snapshot = self._frames.snapshot()
        now = time.perf_counter()
        if snapshot.count != self._count and snapshot.frame is not None:
            previous, self._frame = self._frame, snapshot.frame
            self._count = snapshot.count
            self._image = to_qimage(snapshot.frame)
            self._displayed.tick(now)
            if previous is None or previous.shape != snapshot.frame.shape:
                # The first frame, or the game changed resolution.
                self._fit_to_screen(self._image.size())
            self.update()
        elif now - self._painted_at > IDLE_REDRAW:
            self.update()

    def _fit_to_screen(self, frame: QSize) -> None:
        """Size the window to the frame, or to what the screen has room for,
        and center it there."""
        available = self.screen().availableGeometry()
        room = available.size() * 0.85
        if frame.width() > room.width() or frame.height() > room.height():
            frame = frame.scaled(room, Qt.AspectRatioMode.KeepAspectRatio)
        self.resize(frame)
        outer = self.frameGeometry()
        outer.moveCenter(available.center())
        self.move(outer.topLeft())

    def paintEvent(self, event: QPaintEvent) -> None:
        now = time.perf_counter()
        self._painted_at = now
        painter = QPainter(self)
        painter.fillRect(self.rect(), QColor(8, 10, 14))
        if self._image is not None:
            size = self._image.size().scaled(self.size(), Qt.AspectRatioMode.KeepAspectRatio)
            area = QRectF(
                (self.width() - size.width()) / 2,
                (self.height() - size.height()) / 2,
                size.width(),
                size.height(),
            )
            painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
            painter.drawImage(area, self._image)
            self._hud.paint(painter, area, self._model(), self._hud_scale)
        lines = [*self._stats(), f"Display  {self._displayed.rate(now):5.1f} fps"]
        self._paint_stats(painter, lines)
        painter.end()

    def _paint_stats(self, painter: QPainter, lines: list[str]) -> None:
        """The reader's numbers, in the bottom left corner."""
        theme = self._hud.theme
        font = theme.font(12, QFont.Weight.Normal, mono=True)
        metrics = QFontMetricsF(font)
        line_height = metrics.height() + 2
        width = max(metrics.horizontalAdvance(line) for line in lines) + 24
        height = line_height * len(lines) + 16
        panel = QRectF(12, self.height() - height - 12, width, height)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(theme.panel)
        painter.drawRoundedRect(panel, 8, 8)
        painter.setFont(font)
        painter.setPen(theme.text_dim)
        baseline = panel.top() + 8 + metrics.ascent()
        for line in lines:
            painter.drawText(QPointF(panel.left() + 12, baseline), line)
            baseline += line_height

    def keyPressEvent(self, event: QKeyEvent) -> None:
        if event.key() == Qt.Key.Key_S:
            self.screenshot_requested.emit()
        elif event.key() in (Qt.Key.Key_Q, Qt.Key.Key_Escape):
            self.close()
        else:
            super().keyPressEvent(event)
