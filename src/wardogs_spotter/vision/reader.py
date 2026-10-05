"""Read one frame: the map, the cursor's coordinates and the player's arrow."""

import math

import cv2
import numpy as np

from wardogs_spotter.vision.arrow import find_player
from wardogs_spotter.vision.labels import GlyphReader
from wardogs_spotter.vision.panel import find_map
from wardogs_spotter.vision.reading import MapReading

HOVER = 8  # px; crosshair this close to the arrow means its coordinates are the player's


def read_map(
    frame: np.ndarray, glyphs: GlyphReader, gray: np.ndarray | None = None
) -> MapReading | None:
    """Everything readable on one BGR frame, or None when the map isn't open.
    Pass gray when the caller already converted the frame."""
    if gray is None:
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    found = find_map(gray)
    if found is None:
        return None
    panel, crosshair = found
    reading = MapReading(panel, crosshair)
    text_boxes = []
    if crosshair:
        values, reading.labels = glyphs.read(gray, crosshair)
        text_boxes = [box for _, line in reading.labels for box in line]
        if "x" in values and "y" in values:
            reading.cursor = (values["x"], values["y"])
    player = find_player(frame, gray, panel, text_boxes)
    if player:
        reading.player, reading.heading = player
        # The player's coordinates are exact when the crosshair is on the arrow.
        if reading.cursor and crosshair and math.dist(reading.player, crosshair) <= HOVER:
            reading.player_coords = reading.cursor
    return reading
