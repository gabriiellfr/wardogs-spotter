"""Read the Wardogs in-game map from a captured frame.

With the map open the game draws a crosshair under the mouse and prints its
coordinates next to it (y109.58 above x99.23). This package finds the map and
the crosshair wherever they are, reads those numbers, and finds the player's
arrow (position and heading). Game y grows to the north (up).

Nothing here knows about windows, threads or the HUD: frames in, readings out.

    panel    find the map panel and the crosshair
    labels   read the coordinates printed at the crosshair
    arrow    find the player's arrow and its heading
    reader   the three above on one frame
    tracker  follow the map between frames to get its scale
    annotate mark a reading on its frame, to check by eye
"""

from wardogs_spotter.vision.annotate import describe, draw
from wardogs_spotter.vision.labels import GlyphReader
from wardogs_spotter.vision.panel import find_map
from wardogs_spotter.vision.reader import read_map
from wardogs_spotter.vision.reading import MapReading
from wardogs_spotter.vision.tracker import MapReference, MapTracker

__all__ = [
    "GlyphReader",
    "MapReading",
    "MapReference",
    "MapTracker",
    "describe",
    "draw",
    "find_map",
    "read_map",
]
