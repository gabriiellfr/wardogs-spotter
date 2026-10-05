"""How two cursor readings become a scale, and a scale becomes coordinates."""

import numpy as np
import pytest

from wardogs_spotter.vision import MapReference

STILL = np.array([[1.0, 0, 0], [0, 1.0, 0]])  # the map didn't move


def moved(dx: float = 0, dy: float = 0, zoom: float = 1.0) -> np.ndarray:
    return np.array([[zoom, 0, dx], [0, zoom, dy]])


def calibrated() -> MapReference:
    """A reference at 50 px per unit, with (12, 11) at pixel (200, 50)."""
    reference = MapReference()
    reference.calibrate((100, 100), (10.0, 10.0))
    reference.carry(STILL)
    reference.calibrate((200, 50), (12.0, 11.0))  # 100 px east is 2 units, 50 px up is 1
    return reference


def test_one_reading_is_not_enough():
    reference = MapReference()
    reference.calibrate((100, 100), (10.0, 10.0))
    assert reference.scale is None
    assert reference.coords_at((150, 100)) is None


def test_two_readings_far_enough_apart_give_the_scale():
    assert calibrated().scale == pytest.approx(50)


def test_readings_too_close_together_are_not_trusted():
    reference = MapReference()
    reference.calibrate((100, 100), (10.0, 10.0))
    reference.carry(STILL)
    reference.calibrate((120, 90), (10.4, 10.2))  # under 30 px on both axes
    assert reference.scale is None


def test_axes_that_disagree_give_no_scale():
    reference = MapReference()
    reference.calibrate((100, 100), (10.0, 10.0))
    reference.carry(STILL)
    reference.calibrate((200, 0), (12.0, 11.0))  # 50 px/unit along x, 100 along y
    assert reference.scale is None


def test_coordinates_grow_east_and_north():
    reference = calibrated()
    assert reference.coords_at((250, 50)) == pytest.approx((13.0, 11.0))  # right is east
    assert reference.coords_at((200, 0)) == pytest.approx((12.0, 12.0))  # up is north


def test_panning_keeps_the_scale_and_moves_the_coordinates():
    reference = calibrated()
    reference.carry(moved(dx=40, dy=-20))
    assert reference.scale == pytest.approx(50)
    assert reference.coords_at((240, 30)) == pytest.approx((12.0, 11.0))


def test_zooming_changes_the_scale():
    reference = calibrated()
    reference.carry(moved(zoom=2.0))
    assert reference.scale == pytest.approx(100)
    assert reference.coords_at((400, 100)) == pytest.approx((12.0, 11.0))


def test_a_view_that_could_not_be_followed_drops_everything():
    reference = calibrated()
    reference.carry(None)
    assert reference.scale is None
    assert reference.coords_at((200, 50)) is None


def test_the_freshest_reading_is_the_origin():
    """A reading too close to recalibrate with still pins the coordinates."""
    reference = calibrated()
    reference.carry(STILL)
    reference.calibrate((210, 50), (12.3, 11.0))  # the game says 12.3 here, not 12.2
    assert reference.scale == pytest.approx(50)
    assert reference.coords_at((210, 50)) == pytest.approx((12.3, 11.0))
