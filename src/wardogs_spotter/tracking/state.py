"""What is known about the player and the target, across frames.

The map is open for a few seconds at a time. What it showed (where the player
is, which point the mouse was on last) has to outlive it, so the firing
solution can be read while aiming with the map closed.
"""

from dataclasses import dataclass

from wardogs_spotter.ballistics import FiringSolution, solve
from wardogs_spotter.geometry import Coords, Size
from wardogs_spotter.vision import MapReading


@dataclass(frozen=True)
class PlayerFix:
    """The player's position, as of the last frame that gave it."""

    coords: Coords
    heading: float  # degrees clockwise from north
    seen_at: float  # time.perf_counter() of that frame


@dataclass(frozen=True)
class Target:
    """The last point the mouse was on in the map."""

    coords: Coords
    seen_at: float


@dataclass(frozen=True)
class MapState:
    """Everything the HUD shows; replaced as a whole, never changed in place."""

    reading: MapReading | None = None  # of the latest frame; None while the map is closed
    read_ms: float = 0.0  # how long that frame took to read
    frame_size: Size | None = None  # of the frames being read
    player: PlayerFix | None = None
    target: Target | None = None

    @property
    def solution(self) -> FiringSolution | None:
        """From the last known position to the target, once both are known."""
        if self.player and self.target:
            return solve(self.player.coords, self.target.coords)
        return None

    @property
    def aim(self) -> FiringSolution | None:
        """From the last known position to the point under the cursor right
        now; None while the map is closed or the cursor is on the player."""
        reading = self.reading
        if not (reading and reading.cursor and self.player):
            return None
        if reading.cursor == reading.player_coords:
            return None
        return solve(self.player.coords, reading.cursor)


def advance(
    previous: MapState,
    reading: MapReading | None,
    now: float,
    read_ms: float = 0.0,
    frame_size: Size | None = None,
) -> MapState:
    """The state after one more frame: the frame's reading, plus the position
    and the target it gave, or the previous ones when it gave none."""
    player, target = previous.player, previous.target
    if reading and reading.player_coords and reading.heading is not None:
        player = PlayerFix(reading.player_coords, reading.heading, now)
    # The point under the cursor is the target, unless the cursor is on the
    # player's own arrow. It stays set after the map closes, to aim.
    if reading and reading.cursor and reading.cursor != reading.player_coords:
        target = Target(reading.cursor, now)
    return MapState(reading, read_ms, frame_size, player, target)
