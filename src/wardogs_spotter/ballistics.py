"""Firing solution from the player's position to a target on the in-game map.

Coordinates are the map's: x grows to the east, y to the north, and 1 unit is
100 m (the map's own km ruler puts 10 units between km lines).

So far this is the geometry: horizontal distance and azimuth (degrees clockwise
from north, like the in-game compass). The L81's sight setting for a distance
still needs the L81's own numbers, measured in the game.
"""

import math
from dataclasses import dataclass

from wardogs_spotter.geometry import Coords

METERS_PER_UNIT = 100.0

COMPASS_POINTS = ("N", "NNE", "NE", "ENE", "E", "ESE", "SE", "SSE",
                  "S", "SSW", "SW", "WSW", "W", "WNW", "NW", "NNW")  # fmt: skip


@dataclass(frozen=True)
class FiringSolution:
    distance_m: float
    azimuth_deg: float  # clockwise from north, in [0, 360)

    @property
    def compass_point(self) -> str:
        """The nearest of the 16 compass points, like "ESE"."""
        return compass_point(self.azimuth_deg)


def solve(player: Coords, target: Coords) -> FiringSolution:
    """Distance and azimuth from player to target, both in game coordinates."""
    dx, dy = target[0] - player[0], target[1] - player[1]
    azimuth = math.degrees(math.atan2(dx, dy)) % 360
    if azimuth >= 360:  # a tiny negative angle rounds up to exactly 360
        azimuth = 0.0
    return FiringSolution(math.hypot(dx, dy) * METERS_PER_UNIT, azimuth)


def compass_point(azimuth_deg: float) -> str:
    """The nearest of the 16 compass points to an azimuth in degrees."""
    step = 360 / len(COMPASS_POINTS)
    return COMPASS_POINTS[round(azimuth_deg / step) % len(COMPASS_POINTS)]
