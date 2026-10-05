"""What the HUD shows, worked out from the state: plain values, no drawing.

The painter draws a HudModel and nothing else, so what appears on screen can
be tested without a screen, and the HUD is redrawn only when its model changes.
"""

from dataclasses import dataclass
from enum import Enum

from wardogs_spotter.ballistics import FiringSolution
from wardogs_spotter.geometry import Coords, Pixel, Size
from wardogs_spotter.tracking import MapState

HINT_OPEN_MAP = "Open the map to find your position"
HINT_FIND_ARROW = "Move the mouse over the map, or onto your arrow, to find your position"
HINT_PICK_TARGET = "Put the mouse over your target in the map"


class Fix(Enum):
    """How well the player's position is known."""

    LIVE = "live"  # read from the frame on screen
    STALE = "stale"  # read from an earlier frame
    NONE = "none"  # not read yet


@dataclass(frozen=True)
class MapMarks:
    """What to draw on the open map, in frame pixels."""

    frame_size: Size
    player: Pixel | None = None  # the player's arrow
    heading: float | None = None
    crosshair: Pixel | None = None  # the point being aimed at
    aim: FiringSolution | None = None  # from the player to that point


@dataclass(frozen=True)
class HudModel:
    map_open: bool = False
    fix: Fix = Fix.NONE
    position: Coords | None = None
    heading: float | None = None
    fix_age_s: int | None = None  # seconds since the position was read; None when live
    target: Coords | None = None
    solution: FiringSolution | None = None
    hint: str | None = None  # what to do next, while there is no solution
    marks: MapMarks | None = None  # None while the map is closed
    toast: str | None = None  # a passing message, like "Screenshot saved"


def _fix(state: MapState) -> Fix:
    if state.reading and state.reading.player_coords:
        return Fix.LIVE
    return Fix.STALE if state.player else Fix.NONE


def build_hud(state: MapState, now: float, toast: str | None = None) -> HudModel:
    """The HUD for a state at time `now` (time.perf_counter())."""
    reading = state.reading
    fix = _fix(state)

    hint = None
    if fix is Fix.NONE:
        hint = HINT_FIND_ARROW if reading and reading.player else HINT_OPEN_MAP
    elif state.target is None:
        hint = HINT_PICK_TARGET

    marks = None
    if reading and state.frame_size:
        aim = state.aim
        marks = MapMarks(
            frame_size=state.frame_size,
            player=reading.player,
            heading=reading.heading,
            crosshair=reading.crosshair if aim else None,
            aim=aim,
        )

    player = state.player
    age = None
    if player and fix is Fix.STALE:
        age = int(now - player.seen_at)
        if age >= 60:  # shown in minutes from here on: change once a minute
            age -= age % 60
    return HudModel(
        map_open=reading is not None,
        fix=fix,
        position=player.coords if player else None,
        heading=player.heading if player else None,
        fix_age_s=age,
        target=state.target.coords if state.target else None,
        solution=state.solution,
        hint=hint,
        marks=marks,
        toast=toast,
    )


class Toast:
    """A message that shows for a few seconds."""

    def __init__(self, seconds: float = 2.5) -> None:
        self._seconds = seconds
        self._text: str | None = None
        self._until = 0.0

    def show(self, text: str, now: float) -> None:
        self._text, self._until = text, now + self._seconds

    def current(self, now: float) -> str | None:
        """The message, while it is still due."""
        return self._text if now < self._until else None


def format_coord(value: float) -> str:
    """A game coordinate the way the game prints it."""
    return f"{value:.2f}"


def format_range(solution: FiringSolution) -> str:
    """Whole meters."""
    return f"{solution.distance_m:.0f}"


def format_azimuth(solution: FiringSolution) -> str:
    """Tenths of a degree, never "360.0"."""
    return f"{round(solution.azimuth_deg, 1) % 360:.1f}°"


def format_heading(heading: float) -> str:
    """Three digits, like the in-game compass: 090°."""
    return f"{round(heading) % 360:03d}°"


def format_age(seconds: int) -> str:
    if seconds < 60:
        return f"{seconds} s ago"
    return f"{seconds // 60} min ago"
