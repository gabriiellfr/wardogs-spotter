"""Find the player's arrow on the map, and where it points."""

import math

import cv2
import numpy as np

from wardogs_spotter.geometry import Box, Pixel, Rect

ARROW_SIZES = (7, 9, 12, 16)  # px from tip to back; the arrow grows as the map zooms in
COARSE_STEP = 15  # degrees between the rotations every candidate is tried against
FINE_REACH, FINE_STEP = 12, 3  # degrees around the coarse heading, and between tries
MIN_ARROW = 0.85  # arrowhead match score; in the samples the arrow scored 0.87-0.95,
#                   other white shapes (drill icons of objectives) up to 0.81
MAX_CANDIDATES = 15  # largest white shapes tried as the arrow
SEARCH = 16  # px around a candidate's center the arrowhead may sit

SOLID = cv2.getStructuringElement(cv2.MORPH_RECT, (3, 3))

Templates = dict[int, list[tuple[int, np.ndarray]]]  # length -> (heading, image) pairs
Match = tuple[float, tuple[float, float] | None, int | None, int | None]


def _arrow(length: int, heading: float) -> np.ndarray:
    """The player's arrow as the map draws it: a notched arrowhead, pointing
    at heading (degrees clockwise from north), as a float image."""
    # Proportions measured on a clean screenshot of the arrow, pointing east.
    points = np.array([[0.5, 0], [-0.5, -0.46], [-0.33, 0], [-0.5, 0.46]]) * length
    a = math.radians(heading - 90)
    points = points @ np.array([[math.cos(a), math.sin(a)], [-math.sin(a), math.cos(a)]])
    n = int(length * 1.3) | 1
    img = np.zeros((n, n), np.uint8)
    cv2.fillPoly(img, [np.round(points * 4 + n * 2).astype(np.int32)], 255, cv2.LINE_AA, shift=2)
    return img.astype(np.float32) / 255


# Every rotation of a size has the same image size.
ARROWS: Templates = {
    length: [(heading, _arrow(length, heading)) for heading in range(0, 360, COARSE_STEP)]
    for length in ARROW_SIZES
}


def _best_arrow(whiteness: np.ndarray, cx: int, cy: int, arrows: Templates) -> Match:
    """(score, (x, y) center, heading, length) of the best match in a window
    around (cx, cy)."""
    wx, wy = max(cx - SEARCH, 0), max(cy - SEARCH, 0)
    window = whiteness[wy : cy + SEARCH + 1, wx : cx + SEARCH + 1]
    best: Match = (-1.0, None, None, None)
    for length, rotations in arrows.items():
        th, tw = rotations[0][1].shape
        if th > window.shape[0] or tw > window.shape[1]:
            continue
        # Over a flat patch (inside a solid white block) the normalization
        # divides by almost nothing and can report a perfect 1.0: ignore those.
        mean, sq = (
            cv2.boxFilter(a, -1, (tw, th), normalize=True, anchor=(0, 0))
            for a in (window, window * window)
        )
        rows, cols = window.shape[0] - th + 1, window.shape[1] - tw + 1
        flat = (sq - mean * mean)[:rows, :cols] < 0.02
        for heading, template in rotations:
            scores = cv2.matchTemplate(window, template, cv2.TM_CCOEFF_NORMED)
            scores[flat] = -1
            _, score, _, (mx, my) = cv2.minMaxLoc(scores)
            if score > best[0]:
                best = (score, (wx + mx + tw / 2, wy + my + th / 2), heading, length)
    return best


def find_player(
    frame: np.ndarray, gray: np.ndarray, panel: Rect, text_boxes: list[Box]
) -> tuple[Pixel, int] | None:
    """((px, py), heading) of the player's arrow, or None. Candidates are the
    solid white shapes: an opening (erode, then dilate) removes text, markers
    and the crosshair, which are thin strokes. The arrow is the candidate that
    matches a notched arrowhead at some rotation and size, which tells it apart
    from the white drill icons of objectives even when teammates' green arrows
    cover part of it, and gives the heading. Too small at the farthest zoom."""
    left, top, right, bottom = panel
    x0, y0 = left + 3, top + 3
    g = gray[y0 : bottom - 2, x0 : right - 2]
    sat = cv2.cvtColor(frame[y0 : bottom - 2, x0 : right - 2], cv2.COLOR_BGR2HSV)[..., 1]
    white = ((g > 200) & (sat < 60)).astype(np.uint8)
    for x, y, w, h in text_boxes:  # bold tooltip text survives the opening in spots
        white[max(y - y0 - 1, 0) : y - y0 + h + 1, max(x - x0 - 1, 0) : x - x0 + w + 1] = 0
    whiteness = np.clip((g.astype(np.float32) - 150) / 80, 0, 1) * (sat < 60)
    solid = cv2.morphologyEx(white, cv2.MORPH_OPEN, SOLID)
    _, _, stats, centroids = cv2.connectedComponentsWithStats(solid, connectivity=8)
    candidates = sorted(
        (area, i)
        for i, (_, _, w, h, area) in enumerate(stats[1:], 1)
        if area >= 12 and max(w, h) <= 40
    )[-MAX_CANDIDATES:]
    best: Match = (MIN_ARROW, None, None, None)
    for _, i in candidates:
        found = _best_arrow(whiteness, int(centroids[i][0]), int(centroids[i][1]), ARROWS)
        if found[0] > best[0]:
            best = found
    _, center, heading, length = best
    if center is None or heading is None or length is None:
        return None
    # The candidates are COARSE_STEP degrees apart; settle the heading to FINE_STEP.
    finer: Templates = {
        length: [
            (h, _arrow(length, h))
            for h in range(heading - FINE_REACH, heading + FINE_REACH + 1, FINE_STEP)
        ]
    }
    _, center, heading, _ = _best_arrow(whiteness, int(center[0]), int(center[1]), finer)
    if center is None or heading is None:  # at the panel's edge the window can be too small
        return None
    return (round(center[0]) + x0, round(center[1]) + y0), heading % 360
