"""A transparent, click-through window kept on top of the game.

This is how an overlay works without touching the game: a topmost layered
window that Windows composites over the game, with per-pixel transparency, so
only what is drawn shows and every click goes through to the game. Windows
can't composite anything over a game in exclusive fullscreen, so the game has
to run borderless or windowed. The overlay hides while the game isn't the
foreground window, so it doesn't float over other programs.

Windows Graphics Capture of the game doesn't include the overlay: frames show
only the game, so what the overlay draws never feeds back into the analysis.
"""

from collections.abc import Callable

from PySide6.QtCore import QRectF, Qt, QTimer
from PySide6.QtGui import QPainter, QPaintEvent
from PySide6.QtWidgets import QWidget

from wardogs_spotter import winapi
from wardogs_spotter.geometry import Rect
from wardogs_spotter.ui.hud import HudPainter
from wardogs_spotter.ui.model import HudModel


class OverlayWindow(QWidget):
    """Covers the window that target() returns and paints what model()
    returns over it. It repaints only when the model changes."""

    def __init__(
        self,
        hud: HudPainter,
        target: Callable[[], int | None],
        model: Callable[[], HudModel],
        fps: int = 30,
        scale: float = 1.0,
    ) -> None:
        super().__init__()
        self.setWindowTitle("Wardogs Spotter HUD")
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.Tool  # no taskbar button
            | Qt.WindowType.WindowTransparentForInput  # clicks go through to the game
            | Qt.WindowType.WindowDoesNotAcceptFocus  # never takes focus from the game
            | Qt.WindowType.NoDropShadowWindowHint
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)  # per-pixel transparency
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating)
        self.enabled = True  # False hides the HUD until it is set again
        self._hud = hud
        self._target = target
        self._model = model
        self._scale = scale
        self._shown = HudModel()  # the model on screen
        self._timer = QTimer(self)
        self._timer.setInterval(round(1000 / fps))
        self._timer.timeout.connect(self._refresh)

    def start(self) -> None:
        self._timer.start()

    def _game_bounds(self) -> Rect | None:
        """Where to draw, or None while there is nothing to draw over."""
        game = self._target()
        if not (self.enabled and game):
            return None
        if winapi.foreground_window() != game or winapi.is_minimized(game):
            return None
        left, top, right, bottom = bounds = winapi.window_bounds(game)
        return bounds if right > left and bottom > top else None

    def _refresh(self) -> None:
        bounds = self._game_bounds()
        if bounds is None:
            if self.isVisible():
                self.hide()
            return
        model = self._model()
        if model != self._shown:
            self._shown = model
            self.update()
        # Placed through Win32, in physical pixels like the bounds, so the
        # monitor's scaling can't shift it. Again on every refresh: the game
        # may be topmost itself, and the overlay has to stay above it.
        handle = int(self.winId())
        winapi.place_topmost(handle, bounds)
        if not self.isVisible():
            self.show()
            winapi.place_topmost(handle, bounds)

    def paintEvent(self, event: QPaintEvent) -> None:
        painter = QPainter(self)
        self._hud.paint(painter, QRectF(self.rect()), self._shown, self._scale)
        painter.end()
