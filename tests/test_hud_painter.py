"""The painter draws where it should, and only there. What it looks like is
judged by eye: `wardogs-spotter preview --replay` shows it."""

import numpy as np
import pytest
from PySide6.QtCore import QRectF
from PySide6.QtGui import QImage, QPainter

from wardogs_spotter.ballistics import solve
from wardogs_spotter.ui.hud import BAR_HEIGHT, BAR_WIDTH, MARGIN, HudPainter
from wardogs_spotter.ui.images import compose, to_qimage
from wardogs_spotter.ui.model import Fix, HudModel, MapMarks

SOLUTION = solve((83.0, 73.0), (85.0, 68.0))
CLOSED = HudModel(
    fix=Fix.STALE,
    position=(83.0, 73.0),
    heading=90,
    fix_age_s=47,
    target=(85.0, 68.0),
    solution=SOLUTION,
)
OPEN = HudModel(
    map_open=True,
    fix=Fix.LIVE,
    position=(83.0, 73.0),
    heading=90,
    target=(85.0, 68.0),
    solution=SOLUTION,
    marks=MapMarks((1920, 1080), player=(942, 571), heading=90, crosshair=(991, 696), aim=SOLUTION),
)


def alpha(model: HudModel, width: int = 1920, height: int = 1080, scale: float = 1.0) -> np.ndarray:
    """What the overlay window would show: the opacity of each pixel."""
    image = QImage(width, height, QImage.Format.Format_ARGB32_Premultiplied)
    image.fill(0)
    painter = QPainter(image)
    HudPainter().paint(painter, QRectF(image.rect()), model, scale)
    painter.end()
    pixels = np.frombuffer(image.constBits(), np.uint8).reshape(height, width, 4)
    return pixels[..., 3].copy()


def painted_box(opacity: np.ndarray) -> tuple[int, int, int, int]:
    """(left, top, right, bottom) of everything drawn."""
    rows, cols = np.where(opacity.any(1))[0], np.where(opacity.any(0))[0]
    return int(cols[0]), int(rows[0]), int(cols[-1]), int(rows[-1])


def test_with_the_map_closed_only_the_bar_is_drawn(qapp):
    left, top, right, bottom = painted_box(alpha(CLOSED))
    shadow = 8  # the bar's soft shadow reaches a little past it
    assert left >= MARGIN - shadow and top >= MARGIN - shadow
    assert right <= MARGIN + BAR_WIDTH + shadow
    assert bottom <= MARGIN + BAR_HEIGHT + shadow + 2


def test_the_bar_stays_clear_of_the_games_compass(qapp):
    """The game's compass strip starts at about a third of the width."""
    _, _, right, _ = painted_box(alpha(CLOSED))
    assert right < 1920 * 0.32


def test_the_bar_is_solid_enough_to_read_on(qapp):
    opacity = alpha(CLOSED)
    assert opacity[MARGIN + BAR_HEIGHT // 2, MARGIN + BAR_WIDTH - 12] > 200


def test_marks_are_drawn_on_the_open_map(qapp):
    opacity = alpha(OPEN)
    ring = opacity[571 - 22 : 571 + 22, 942 - 22 : 942 + 22]
    target = opacity[696 - 8 : 696 + 8, 991 - 8 : 991 + 8]
    assert ring.max() > 200 and target.max() > 200
    assert opacity[571, 942] == 0  # the arrow itself stays visible inside the ring
    assert opacity[696, 991] == 0  # and so does the point under the cursor


def test_the_hud_grows_with_the_game(qapp):
    """At twice the resolution it covers the same part of the picture."""
    small = painted_box(alpha(OPEN, 1920, 1080))
    large = painted_box(alpha(OPEN, 3840, 2160))
    assert large == pytest.approx([2 * edge for edge in small], abs=6)


def test_scale_makes_the_bar_bigger(qapp):
    _, _, right, bottom = painted_box(alpha(CLOSED))
    _, _, big_right, big_bottom = painted_box(alpha(CLOSED, scale=1.5))
    assert big_right > right * 1.4 and big_bottom > bottom * 1.4


def test_a_toast_is_drawn_under_the_bar(qapp):
    from dataclasses import replace

    plain = alpha(CLOSED)
    with_toast = alpha(replace(CLOSED, toast="Screenshot saved"))
    below = slice(MARGIN + BAR_HEIGHT + 12, MARGIN + BAR_HEIGHT + 36)
    assert not plain[below, MARGIN + 20 : MARGIN + 120].any()
    assert with_toast[below, MARGIN + 20 : MARGIN + 120].max() > 200


def test_every_state_paints_without_error(qapp):
    for model in (HudModel(), HudModel(hint="Open the map"), HudModel(target=(1.0, 2.0)), OPEN):
        assert alpha(model).any()


def test_compose_leaves_the_frame_alone(qapp, frames):
    frame = frames[3]
    before = frame.copy()
    image = compose(frame, HudPainter(), CLOSED)
    assert (image.width(), image.height()) == (frame.shape[1], frame.shape[0])
    assert (frame == before).all()
    assert image.pixelColor(MARGIN + 40, MARGIN + 36) != to_qimage(frame).pixelColor(
        MARGIN + 40, MARGIN + 36
    )
