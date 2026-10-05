"""Follow the map from frame to frame to work out its scale.

The player's coordinates are only printed when the crosshair is on the arrow.
For the rest, MapTracker follows the map by matching its texture, so it knows
how the view panned and zoomed. A cursor reading from an earlier frame, carried
into the current one, and the current reading give the scale (pixels per game
unit), and with it the coordinates of every map pixel, the player's arrow
included.
"""

import math
from dataclasses import dataclass

import cv2
import numpy as np

from wardogs_spotter.geometry import Coords, Pixel
from wardogs_spotter.vision.labels import GlyphReader
from wardogs_spotter.vision.reader import read_map
from wardogs_spotter.vision.reading import MapReading

MIN_MOVE = 30  # px the cursor must move over the map before two readings give the scale
MIN_MATCHES = 30  # matched map features that agree on a pan and zoom; fewer is a new view
MAX_AXIS_DISAGREEMENT = 1.05  # the scales measured along x and y may differ by 5%


@dataclass(frozen=True)
class _Anchor:
    """A map pixel whose game coordinates are known."""

    pixel: tuple[float, float]
    coords: Coords


class MapReference:
    """What turns map pixels into game coordinates: a pixel with known
    coordinates, and the scale. Each frame it is carried along with the map's
    movement, then calibrated with the frame's cursor reading if there is one."""

    def __init__(self) -> None:
        self.scale: float | None = None  # map pixels per game unit, once measured
        self._anchor: _Anchor | None = None  # the reading the scale is measured against
        self._origin: _Anchor | None = None  # the reading coordinates are measured from

    def reset(self) -> None:
        self.scale = self._anchor = self._origin = None

    def carry(self, move: np.ndarray | None) -> None:
        """Take the reference into the next frame, given the 2x3 transform of
        the map's pan and zoom since the last one. None means the view could
        not be followed, and what was known no longer applies."""
        if move is None:
            self.scale = self._anchor = None
        elif self._anchor:
            x, y = move @ (*self._anchor.pixel, 1)
            self._anchor = _Anchor((float(x), float(y)), self._anchor.coords)
            if self.scale:
                self.scale *= math.hypot(move[0, 0], move[1, 0])  # zooming changes the scale
        self._origin = self._anchor

    def calibrate(self, crosshair: Pixel, cursor: Coords) -> None:
        """Take in a cursor reading of the current frame. Once the cursor is
        MIN_MOVE px from the carried reading, the two give the scale."""
        here = _Anchor(crosshair, cursor)
        self._origin = here  # the freshest reading is exact
        if self._anchor is None:
            self._anchor = here
            return
        (ax, ay), (gx, gy) = self._anchor.pixel, self._anchor.coords
        (cx, cy), (x, y) = here.pixel, here.coords
        pairs = ((cx - ax, x - gx), (cy - ay, gy - y))  # game y grows upward
        if any(abs(d_px) >= MIN_MOVE for d_px, _ in pairs):
            ratios = [d_px / d_game for d_px, d_game in pairs if abs(d_px) >= MIN_MOVE and d_game]
            consistent = (
                ratios and min(ratios) > 0 and max(ratios) <= MAX_AXIS_DISAGREEMENT * min(ratios)
            )
            self.scale = sum(ratios) / len(ratios) if consistent else None
            self._anchor = here

    def coords_at(self, pixel: Pixel) -> Coords | None:
        """Game coordinates of a map pixel of the current frame, or None
        until the scale is known."""
        if not (self.scale and self._origin):
            return None
        (ox, oy), (gx, gy) = self._origin.pixel, self._origin.coords
        return gx + (pixel[0] - ox) / self.scale, gy - (pixel[1] - oy) / self.scale


@dataclass(frozen=True)
class _Features:
    """Corners of the map texture in one frame."""

    points: np.ndarray  # (n, 2) positions in the frame
    descriptors: np.ndarray | None  # None when the view has no texture to describe


class MapTracker:
    """Reads frames in order, following the map as it pans and zooms, so each
    reading can carry the scale and the player's coordinates."""

    def __init__(self, glyphs: GlyphReader | None = None) -> None:
        self.glyphs = glyphs or GlyphReader()
        self._orb = cv2.ORB.create(1500, fastThreshold=10)
        self._matcher = cv2.BFMatcher(cv2.NORM_HAMMING, crossCheck=True)
        self._features: _Features | None = None  # of the previous map view
        self._reference = MapReference()

    def update(self, frame: np.ndarray) -> MapReading | None:
        """Read the next BGR frame; None when the map isn't open."""
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        reading = read_map(frame, self.glyphs, gray)
        if reading is None:
            self._features = None
            self._reference.reset()
            return None
        self._reference.carry(self._follow(self._describe(gray, reading)))
        if reading.cursor and reading.crosshair:
            self._reference.calibrate(reading.crosshair, reading.cursor)
        reading.scale = self._reference.scale
        if reading.player and reading.player_coords is None:
            reading.player_coords = self._reference.coords_at(reading.player)
        return reading

    def _describe(self, gray: np.ndarray, reading: MapReading) -> _Features:
        """Corners of the map texture, leaving out what moves with the cursor."""
        left, top, right, bottom = reading.panel
        mask = np.full((bottom - top, right - left), 255, np.uint8)
        mask[:4], mask[-3:], mask[:, :4], mask[:, -3:] = 0, 0, 0, 0
        if reading.crosshair:
            cx, cy = reading.crosshair[0] - left, reading.crosshair[1] - top
            mask[:, max(cx - 6, 0) : cx + 7] = 0
            mask[max(cy - 6, 0) : cy + 7] = 0
            mask[max(cy - 90, 0) : cy + 5, max(cx - 5, 0) : cx + 130] = 0  # coordinate labels
            mask[max(cy - 5, 0) : cy + 175, max(cx - 165, 0) : cx + 5] = 0  # tooltips
        keypoints, descriptors = self._orb.detectAndCompute(gray[top:bottom, left:right], mask)
        points = np.array([k.pt for k in keypoints], np.float32).reshape(-1, 2)
        return _Features(points + np.array((left, top)), descriptors)

    def _follow(self, features: _Features) -> np.ndarray | None:
        """2x3 transform taking the previous frame's map onto this one (pan and
        zoom), or None when the views don't match. Remembers this frame's
        features for the next call."""
        previous, self._features = self._features, features
        if previous is None or previous.descriptors is None or features.descriptors is None:
            return None
        matches = self._matcher.match(previous.descriptors, features.descriptors)
        if len(matches) < MIN_MATCHES:
            return None
        src = previous.points[[m.queryIdx for m in matches]]
        dst = features.points[[m.trainIdx for m in matches]]
        move, inliers = cv2.estimateAffinePartial2D(
            src, dst, method=cv2.RANSAC, ransacReprojThreshold=2.0
        )
        if move is None or inliers.sum() < MIN_MATCHES:
            return None
        return move
