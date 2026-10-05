"""What one frame of the open map tells us."""

from dataclasses import dataclass, field

from wardogs_spotter.geometry import Box, Coords, Pixel, Rect

LabelLine = tuple[str, list[Box]]  # the text read from a line and the box of each glyph


@dataclass
class MapReading:
    panel: Rect  # the map in the frame
    crosshair: Pixel | None = None  # None when the mouse is off the map
    cursor: Coords | None = None  # game coordinates printed at the crosshair
    player: Pixel | None = None  # the player's arrow in the frame
    heading: float | None = None  # degrees clockwise from north
    player_coords: Coords | None = None  # when it can be worked out
    scale: float | None = None  # map pixels per game unit, once known
    labels: list[LabelLine] = field(default_factory=list)  # as read, to check by eye
