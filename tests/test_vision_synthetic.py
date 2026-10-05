"""The reader's stages on images drawn for the test, where the right answer is
known because the test put it there."""

import cv2
import numpy as np
import pytest

from wardogs_spotter.vision import find_map
from wardogs_spotter.vision.arrow import _arrow, find_player

PANEL = (100, 60, 500, 460)


def map_frame(crosshair=None) -> np.ndarray:
    """A gray frame with a map panel outlined the way the game draws it."""
    gray = np.full((540, 640), 40, np.uint8)
    left, top, right, bottom = PANEL
    cv2.rectangle(gray, (left, top), (right, bottom), 200, 1)
    if crosshair:
        cx, cy = crosshair
        cv2.line(gray, (cx, top), (cx, bottom), 200, 1)
        cv2.line(gray, (left, cy), (right, cy), 200, 1)
    return gray


def test_finds_the_panel_and_no_crosshair_when_the_mouse_is_off_the_map():
    assert find_map(map_frame()) == (PANEL, None)


def test_finds_the_crosshair():
    assert find_map(map_frame(crosshair=(260, 300))) == (PANEL, (260, 300))


def test_no_map_on_a_frame_without_one():
    assert find_map(np.full((540, 640), 40, np.uint8)) is None


def test_no_map_on_a_noisy_frame():
    noise = np.random.default_rng(0).integers(0, 255, (540, 640), dtype=np.uint8)
    assert find_map(noise) is None


@pytest.mark.parametrize("heading", [0, 45, 120, 282, 333])
@pytest.mark.parametrize(
    ("length", "tolerance"),
    [(16, 3), (9, 9)],  # a 9 px arrow has too few pixels to tell 3 degrees apart
)
def test_finds_the_arrow_and_its_heading(heading, length, tolerance):
    gray = map_frame()
    arrow = (_arrow(length, heading) * 255).astype(np.uint8)
    n = arrow.shape[0]
    center = (300, 220)
    top, left = center[1] - n // 2, center[0] - n // 2
    gray[top : top + n, left : left + n] = np.maximum(gray[top : top + n, left : left + n], arrow)
    frame = cv2.cvtColor(gray, cv2.COLOR_GRAY2BGR)

    found = find_player(frame, gray, PANEL, text_boxes=[])

    assert found is not None
    (px, py), found_heading = found
    assert abs(px - center[0]) <= 1 and abs(py - center[1]) <= 1
    off = (found_heading - heading + 180) % 360 - 180
    assert abs(off) <= tolerance


def test_a_white_square_is_not_the_arrow():
    gray = map_frame()
    cv2.rectangle(gray, (290, 210), (304, 224), 255, -1)
    frame = cv2.cvtColor(gray, cv2.COLOR_GRAY2BGR)
    assert find_player(frame, gray, PANEL, text_boxes=[]) is None
