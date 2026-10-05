"""Paint the HUD: a bar with the firing solution, the marks on the open map,
and passing messages.

HudPainter draws on any QPainter, so the same code paints the overlay over the
game, the preview window and the copies of screenshots saved with the HUD on.
"""

import math

from PySide6.QtCore import QPointF, QRectF, QSizeF, Qt
from PySide6.QtGui import QColor, QFont, QFontMetricsF, QPainter, QPen, QPolygonF

from wardogs_spotter.ballistics import FiringSolution
from wardogs_spotter.geometry import Coords
from wardogs_spotter.ui.model import (
    Fix,
    HudModel,
    MapMarks,
    format_age,
    format_azimuth,
    format_coord,
    format_range,
)
from wardogs_spotter.ui.theme import Theme

REFERENCE_HEIGHT = 1080  # the game height the sizes below are for

# The bar. It is a strip in the top left corner, a place the game's own HUD
# leaves free: it ends above the game's corner widget and before its compass.
MARGIN = 16  # from the corner of the game window
BAR_HEIGHT = 72
PAD = 16
RADIUS = 14
DIAL_RADIUS = 21
SOLUTION_WIDTH = 246  # the range and azimuth columns
RANGE_WIDTH = 100
DETAILS_WIDTH = 222  # the position and target lines
BAR_WIDTH = PAD + 2 * DIAL_RADIUS + PAD + SOLUTION_WIDTH + PAD + DETAILS_WIDTH + PAD
UPPER, LOWER = 31, 53  # baselines of the two lines of small text, from the bar's top
TOAST_HEIGHT = 30

Segment = tuple[str, QFont, QColor]  # a run of text in one style


class HudPainter:
    """Paints a HudModel. It keeps nothing between calls."""

    def __init__(self, theme: Theme | None = None) -> None:
        self.theme = theme or Theme()

    def paint(self, painter: QPainter, area: QRectF, model: HudModel, scale: float = 1.0) -> None:
        """Paint the model over `area`, which is where the game's image is.
        The HUD grows with the area, as the game's own HUD does with the
        resolution, so it covers the same part of the picture at any size;
        `scale` makes it larger or smaller than that."""
        scale *= area.height() / REFERENCE_HEIGHT
        painter.save()
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setRenderHint(QPainter.RenderHint.TextAntialiasing)
        painter.setClipRect(area)
        painter.translate(area.topLeft())
        if model.marks:
            self._paint_marks(painter, area.size(), model.marks, scale)
        painter.scale(scale, scale)
        bar = QRectF(MARGIN, MARGIN, BAR_WIDTH, BAR_HEIGHT)
        self._paint_bar(painter, bar, model)
        if model.toast:
            self._paint_toast(painter, bar, model.toast)
        painter.restore()

    # The bar

    def _paint_bar(self, p: QPainter, bar: QRectF, model: HudModel) -> None:
        """A compass dial, then either the solution with the coordinates it
        came from, or what to do to get one."""
        theme = self.theme
        self._paint_panel(p, bar, RADIUS)
        center = QPointF(bar.left() + PAD + DIAL_RADIUS, bar.center().y())
        self._paint_dial(p, center, DIAL_RADIUS, model.solution)
        x = center.x() + DIAL_RADIUS + PAD
        upper, lower = bar.top() + UPPER, bar.top() + LOWER

        if model.solution:
            self._paint_solution(p, x, bar.top(), model.solution)
            x += SOLUTION_WIDTH
            p.setPen(QPen(theme.divider, 1))
            p.drawLine(QPointF(x + 0.5, bar.top() + 15), QPointF(x + 0.5, bar.bottom() - 15))
            x += PAD
            self._paint_position(p, x, upper, model)
            self._paint_target(p, x, lower, model)
            return

        font = theme.font(13.5, QFont.Weight.Medium)
        room = bar.right() - PAD - x
        hint = QFontMetricsF(font).elidedText(model.hint or "", Qt.TextElideMode.ElideRight, room)
        self._text(p, x, upper, hint, font, theme.text)
        if model.position is not None:
            self._paint_position(p, x, lower, model)
        elif model.target is not None:
            self._paint_target(p, x, lower, model)
        else:
            brand = theme.font(10, QFont.Weight.DemiBold, spacing=2.2)
            self._text(p, x, lower, "WARDOGS SPOTTER", brand, theme.text_faint)

    def _paint_panel(self, p: QPainter, rect: QRectF, radius: float) -> None:
        """A dark translucent surface with a hairline border and a soft shadow."""
        theme = self.theme
        p.setPen(Qt.PenStyle.NoPen)
        for spread in (6, 4, 2):  # stacked, they fade outward like a blur
            p.setBrush(theme.shadow)
            grown = rect.adjusted(-spread, -spread + 2, spread, spread + 2)
            p.drawRoundedRect(grown, radius + spread, radius + spread)
        p.setBrush(theme.panel)
        p.drawRoundedRect(rect, radius, radius)
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.setPen(QPen(theme.panel_border, 1))
        p.drawRoundedRect(rect.adjusted(0.5, 0.5, -0.5, -0.5), radius, radius)

    def _paint_solution(self, p: QPainter, x: float, top: float, solution: FiringSolution) -> None:
        """Range and azimuth in large type."""
        theme = self.theme
        label = theme.font(10, QFont.Weight.DemiBold, spacing=1.4)
        value = theme.font(30, QFont.Weight.DemiBold)
        unit = theme.font(13, QFont.Weight.Medium)
        label_baseline, value_baseline = top + 24, top + 56

        self._text(p, x, label_baseline, "RANGE", label, theme.text_dim)
        distance: list[Segment] = [
            (format_range(solution), value, theme.text),
            (" m", unit, theme.text_dim),
        ]
        self._run(p, x - 1, value_baseline, distance)

        x += RANGE_WIDTH
        self._text(p, x, label_baseline, "AZIMUTH", label, theme.text_dim)
        azimuth: list[Segment] = [
            (format_azimuth(solution), value, theme.target),
            (" " + solution.compass_point, unit, theme.text_dim),
        ]
        self._run(p, x - 1, value_baseline, azimuth)

    def _paint_dial(
        self, p: QPainter, center: QPointF, radius: float, solution: FiringSolution | None
    ) -> None:
        """A north-up compass, with a needle at the azimuth when there is one."""
        theme = self.theme
        p.setBrush(QColor(255, 255, 255, 10))
        p.setPen(QPen(theme.panel_border, 1.2))
        p.drawEllipse(center, radius, radius)
        for degrees in range(0, 360, 30):
            cardinal = degrees % 90 == 0
            direction = _direction(degrees)
            if degrees == 0:  # north stands out, to read the needle against
                p.setPen(QPen(theme.text, 1.6))
            else:
                p.setPen(QPen(theme.text_dim if cardinal else theme.text_faint, 1.2))
            inner = radius - (5.5 if cardinal else 3.5)
            p.drawLine(center + direction * inner, center + direction * (radius - 1.5))
        if solution is None:
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(theme.text_faint)
            p.drawEllipse(center, 2.2, 2.2)
            return

        direction = _direction(solution.azimuth_deg)
        side = QPointF(-direction.y(), direction.x())
        tip = center + direction * (radius - 6)
        needle = QPen(theme.target, 2.0)
        needle.setCapStyle(Qt.PenCapStyle.RoundCap)
        p.setPen(needle)
        p.drawLine(center - direction * 4.5, center + direction * (radius - 11))
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(theme.target)
        p.drawPolygon(
            QPolygonF([tip, tip - direction * 7 + side * 3.8, tip - direction * 7 - side * 3.8])
        )
        p.setBrush(theme.panel)
        p.setPen(QPen(theme.target, 1.5))
        p.drawEllipse(center, 2.5, 2.5)

    def _paint_position(self, p: QPainter, x: float, baseline: float, model: HudModel) -> None:
        """Where the player is, and how fresh that is."""
        if model.position is None:
            return
        theme = self.theme
        x = self._paint_coords(p, x, baseline, "YOU", theme.you, model.position)
        tag = theme.font(10, QFont.Weight.DemiBold, spacing=1.2)
        if model.fix is Fix.LIVE:
            self._text(p, x, baseline, "LIVE", tag, theme.live)
        elif model.fix_age_s is not None:
            self._text(p, x, baseline, format_age(model.fix_age_s).upper(), tag, theme.stale)

    def _paint_target(self, p: QPainter, x: float, baseline: float, model: HudModel) -> None:
        if model.target is not None:
            self._paint_coords(p, x, baseline, "TGT", self.theme.target, model.target)

    def _paint_coords(
        self, p: QPainter, x: float, baseline: float, tag: str, color: QColor, coords: Coords
    ) -> float:
        """A tag and a pair of coordinates, written the way the game prints
        them. Returns the x where more can follow."""
        theme = self.theme
        self._text(p, x, baseline, tag, theme.font(10, QFont.Weight.Bold, spacing=1.4), color)
        font = theme.font(13, QFont.Weight.Medium)
        x += 38
        for axis, value in zip("xy", coords, strict=True):
            segments: list[Segment] = [
                (axis + " ", font, theme.text_dim),
                (format_coord(value), font, theme.text),
            ]
            self._run(p, x, baseline, segments)
            x += 62
        return x

    # The marks on the map

    def _paint_marks(self, p: QPainter, area: QSizeF, marks: MapMarks, ui: float) -> None:
        """A ring on the player's arrow with a pointer at the heading, and a
        line from there to the point under the cursor with the solution."""
        theme = self.theme
        zoom = area.width() / marks.frame_size[0]  # frame pixels to area pixels
        player = QPointF(marks.player[0], marks.player[1]) * zoom if marks.player else None
        aim_at = None
        if marks.crosshair and marks.aim:
            aim_at = QPointF(marks.crosshair[0], marks.crosshair[1]) * zoom
        ring = 13 * zoom + 3 * ui

        if player is not None and aim_at is not None:
            offset = aim_at - player
            length = math.hypot(offset.x(), offset.y())
            if length > ring + 14 * ui:
                along = offset / length
                start, end = player + along * (ring + 2 * ui), aim_at - along * (7 * ui)
                self._line(p, start, end, theme.target, 1.6 * ui, dash=(5.0, 4.0))

        if player is not None:
            p.setBrush(Qt.BrushStyle.NoBrush)
            p.setPen(QPen(theme.halo, 4.6 * ui))
            p.drawEllipse(player, ring, ring)
            p.setPen(QPen(theme.you, 2.0 * ui))
            p.drawEllipse(player, ring, ring)
            if marks.heading is not None:
                direction = _direction(marks.heading)
                side = QPointF(-direction.y(), direction.x())
                tip = player + direction * (ring + 11 * ui)
                base = player + direction * (ring + 3 * ui)
                pointer = QPolygonF([tip, base + side * (4.5 * ui), base - side * (4.5 * ui)])
                p.setPen(QPen(theme.halo, 2.4 * ui))
                p.setBrush(theme.you)
                p.drawPolygon(pointer)

        if aim_at is not None and marks.aim is not None:
            p.setBrush(Qt.BrushStyle.NoBrush)
            p.setPen(QPen(theme.halo, 4.2 * ui))
            p.drawEllipse(aim_at, 5.5 * ui, 5.5 * ui)
            p.setPen(QPen(theme.target, 1.8 * ui))
            p.drawEllipse(aim_at, 5.5 * ui, 5.5 * ui)
            self._paint_chip(p, aim_at, area, marks.aim, ui)

    def _paint_chip(
        self, p: QPainter, anchor: QPointF, area: QSizeF, aim: FiringSolution, ui: float
    ) -> None:
        """The solution in a pill next to the cursor: below and to the right,
        because the game prints x and y above it and tooltips to the left."""
        theme = self.theme
        value = theme.font(14 * ui, QFont.Weight.DemiBold)
        unit = theme.font(12 * ui, QFont.Weight.Medium)
        segments: list[Segment] = [
            (format_range(aim), value, theme.text),
            (" m", unit, theme.text_dim),
            ("    ", unit, theme.text_dim),
            (format_azimuth(aim), value, theme.target),
            (" " + aim.compass_point, unit, theme.text_dim),
        ]
        width = self._run_width(segments) + 24 * ui
        height, gap = 28 * ui, 14 * ui
        x, y = anchor.x() + gap, anchor.y() + gap
        if x + width > area.width() - 4:
            x, y = anchor.x() - gap - width, anchor.y() - gap - height
        elif y + height > area.height() - 4:
            y = anchor.y() - gap - height
        rect = QRectF(x, y, width, height)
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(theme.panel)
        p.drawRoundedRect(rect, height / 2, height / 2)
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.setPen(QPen(theme.panel_border, 1))
        p.drawRoundedRect(rect.adjusted(0.5, 0.5, -0.5, -0.5), height / 2, height / 2)
        self._run(p, x + 12 * ui, y + height - 9 * ui, segments)

    # Passing messages

    def _paint_toast(self, p: QPainter, bar: QRectF, text: str) -> None:
        """A pill under the bar."""
        theme = self.theme
        font = theme.font(12.5, QFont.Weight.Medium)
        width = QFontMetricsF(font).horizontalAdvance(text) + 40
        rect = QRectF(bar.left(), bar.bottom() + 8, width, TOAST_HEIGHT)
        self._paint_panel(p, rect, TOAST_HEIGHT / 2)
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(theme.live)
        p.drawEllipse(QPointF(rect.left() + 15, rect.center().y()), 3, 3)
        self._text(p, rect.left() + 26, rect.bottom() - 10.5, text, font, theme.text)

    # Primitives

    def _line(
        self,
        p: QPainter,
        start: QPointF,
        end: QPointF,
        color: QColor,
        width: float,
        dash: tuple[float, float] | None = None,
    ) -> None:
        """A line that reads over any part of the map: dark underneath, color on top."""
        under = QPen(self.theme.halo, width + 2.6)
        under.setCapStyle(Qt.PenCapStyle.RoundCap)
        p.setPen(under)
        p.drawLine(start, end)
        over = QPen(color, width)
        over.setCapStyle(Qt.PenCapStyle.FlatCap)
        if dash:
            over.setDashPattern(list(dash))
        p.setPen(over)
        p.drawLine(start, end)

    @staticmethod
    def _text(
        p: QPainter, x: float, baseline: float, text: str, font: QFont, color: QColor
    ) -> float:
        """Draw text from x. Returns its width."""
        p.setFont(font)
        p.setPen(color)
        p.drawText(QPointF(x, baseline), text)
        return QFontMetricsF(font).horizontalAdvance(text)

    def _run(self, p: QPainter, x: float, baseline: float, segments: list[Segment]) -> float:
        """Draw segments one after the other. Returns the x where they end."""
        for text, font, color in segments:
            x += self._text(p, x, baseline, text, font, color)
        return x

    @staticmethod
    def _run_width(segments: list[Segment]) -> float:
        return sum(QFontMetricsF(font).horizontalAdvance(text) for text, font, _ in segments)


def _direction(degrees: float) -> QPointF:
    """Unit vector on screen for a compass direction (clockwise from north)."""
    radians = math.radians(degrees)
    return QPointF(math.sin(radians), -math.cos(radians))
