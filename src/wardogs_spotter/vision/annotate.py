"""Mark a reading on a copy of its frame, to check the reader by eye."""

import math

import cv2
import numpy as np

from wardogs_spotter.geometry import format_coords
from wardogs_spotter.vision.reading import MapReading

PANEL_COLOR = (255, 255, 0)  # BGR
LABEL_COLOR = (0, 200, 255)
PLAYER_COLOR = (0, 0, 255)
TEXT_COLOR = (0, 255, 0)


def describe(reading: MapReading) -> str:
    """One line summing up a reading."""
    cursor = format_coords(reading.cursor) if reading.cursor else "-"
    if reading.player_coords:
        player = format_coords(reading.player_coords)
    else:
        player = "on map" if reading.player else "-"
    heading = f"{reading.heading:.0f}" if reading.heading is not None else "-"
    scale = f"{reading.scale:.1f} px/unit" if reading.scale else "-"
    return f"cursor {cursor:16} player {player:16} heading {heading:>3}  scale {scale}"


def _text(img: np.ndarray, text: str, org: tuple[int, int], scale: float = 0.8) -> None:
    """Text on a black backing. (A thick black copy as outline doesn't work:
    OpenCV 5 draws thicker text wider.)"""
    (w, h), base = cv2.getTextSize(text, cv2.FONT_HERSHEY_SIMPLEX, scale, 1)
    x, y = org
    cv2.rectangle(img, (x - 4, y - h - 4), (x + w + 4, y + base + 2), (0, 0, 0), -1)
    cv2.putText(img, text, org, cv2.FONT_HERSHEY_SIMPLEX, scale, TEXT_COLOR, 1, cv2.LINE_AA)


def draw(frame: np.ndarray, reading: MapReading) -> np.ndarray:
    """A copy of the frame with what was read marked on it: the panel, the
    label lines, the player's arrow and heading, and the summary as text."""
    img = frame.copy()
    cv2.rectangle(img, reading.panel[:2], reading.panel[2:], PANEL_COLOR, 1)
    for _, line in reading.labels:
        x, y = line[0][0], line[0][1]
        w = line[-1][0] + line[-1][2] - x
        h = max(box[1] + box[3] for box in line) - y
        cv2.rectangle(img, (x - 2, y - 2), (x + w + 2, y + h + 2), LABEL_COLOR, 1)
    if reading.player and reading.heading is not None:
        px, py = reading.player
        heading = math.radians(reading.heading)
        end = (int(px + 30 * math.sin(heading)), int(py - 30 * math.cos(heading)))
        cv2.circle(img, (px, py), 12, PLAYER_COLOR, 2)
        cv2.line(img, (px, py), end, PLAYER_COLOR, 2)
    parts = [part.strip() for part in describe(reading).split("  ") if part.strip()]
    for i, part in enumerate(parts):
        _text(img, part, (20, 40 + 30 * i))
    return img
