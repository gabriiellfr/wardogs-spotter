"""The icon in the notification area: the way to reach the program while the
game has the screen."""

from collections.abc import Callable

from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import QAction, QColor, QIcon, QImage, QPainter, QPen, QPixmap
from PySide6.QtWidgets import QMenu, QSystemTrayIcon

from wardogs_spotter.ui.theme import Theme


def draw_icon(size: int = 64, theme: Theme | None = None) -> QImage:
    """The program's icon, drawn rather than shipped: a target ring with the
    player's dot in it. The build draws it larger for the executable."""
    theme = theme or Theme()
    image = QImage(size, size, QImage.Format.Format_ARGB32_Premultiplied)
    image.fill(Qt.GlobalColor.transparent)
    p = QPainter(image)
    p.setRenderHint(QPainter.RenderHint.Antialiasing)
    p.scale(size / 64, size / 64)  # the shapes below are laid out on a 64 px grid
    p.setPen(Qt.PenStyle.NoPen)
    p.setBrush(QColor(11, 14, 20))
    p.drawRoundedRect(QRectF(2, 2, 60, 60), 14, 14)
    center = QPointF(32, 32)
    p.setBrush(Qt.BrushStyle.NoBrush)
    p.setPen(QPen(theme.target, 5))
    p.drawEllipse(center, 17, 17)
    tick = QPen(theme.target, 5)
    tick.setCapStyle(Qt.PenCapStyle.RoundCap)
    p.setPen(tick)
    for dx, dy in ((0, -1), (1, 0), (0, 1), (-1, 0)):
        p.drawLine(center + QPointF(dx, dy) * 17, center + QPointF(dx, dy) * 25)
    p.setPen(Qt.PenStyle.NoPen)
    p.setBrush(theme.you)
    p.drawEllipse(center, 6, 6)
    p.end()
    return image


def app_icon() -> QIcon:
    return QIcon(QPixmap.fromImage(draw_icon()))


class Tray(QSystemTrayIcon):
    """A menu to hide the HUD, save a screenshot, open the screenshots and quit."""

    def __init__(
        self,
        icon: QIcon,
        *,
        on_toggle_hud: Callable[[bool], None],
        on_screenshot: Callable[[], None],
        on_open_screenshots: Callable[[], None],
        on_quit: Callable[[], None],
    ) -> None:
        super().__init__(icon)
        self.setToolTip("Wardogs Spotter")
        self._menu = QMenu()  # kept: the tray icon doesn't own its menu
        self._show_hud = QAction("Show HUD\tF9", self._menu)
        self._show_hud.setCheckable(True)
        self._show_hud.setChecked(True)
        self._show_hud.toggled.connect(on_toggle_hud)
        self._menu.addAction(self._show_hud)
        self._menu.addAction("Save screenshot\tF8", on_screenshot)
        self._menu.addAction("Open screenshots folder", on_open_screenshots)
        self._menu.addSeparator()
        self._menu.addAction("Quit", on_quit)
        self.setContextMenu(self._menu)

    def set_hud_shown(self, shown: bool) -> None:
        """Tick or untick "Show HUD" after the hotkey changed it."""
        self._show_hud.setChecked(shown)
