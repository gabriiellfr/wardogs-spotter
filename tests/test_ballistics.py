import pytest

from wardogs_spotter.ballistics import compass_point, solve


@pytest.mark.parametrize(
    ("target", "azimuth"),
    [
        ((10, 11), 0),  # north: game y grows upward
        ((11, 11), 45),
        ((11, 10), 90),
        ((10, 9), 180),
        ((9, 10), 270),
        ((9, 11), 315),
    ],
)
def test_azimuth_is_clockwise_from_north(target, azimuth):
    assert solve((10, 10), target).azimuth_deg == pytest.approx(azimuth)


def test_one_map_unit_is_100_m():
    assert solve((0, 0), (3, 4)).distance_m == pytest.approx(500)


def test_azimuth_never_reaches_360():
    # A hair west of north: the angle is a tiny negative number, which wraps to 360.
    solution = solve((0, 0), (-1e-18, 1))
    assert 0 <= solution.azimuth_deg < 360


def test_target_on_the_player_is_zero_range():
    solution = solve((5, 5), (5, 5))
    assert solution.distance_m == 0
    assert solution.azimuth_deg == 0


@pytest.mark.parametrize(
    ("azimuth", "point"),
    [(0, "N"), (11.2, "N"), (11.3, "NNE"), (90, "E"), (158.6, "SSE"), (348.8, "N"), (359.9, "N")],
)
def test_compass_point(azimuth, point):
    assert compass_point(azimuth) == point


def test_solution_names_its_compass_point():
    assert solve((0, 0), (-1, -1)).compass_point == "SW"
