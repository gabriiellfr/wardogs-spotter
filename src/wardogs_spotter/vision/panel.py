"""Find the map panel and the crosshair in a frame."""

import numpy as np

from wardogs_spotter.geometry import Pixel, Rect

RIDGE_REACH = 3  # px to each side a line must be brighter than
RIDGE_CONTRAST = 30  # gray levels brighter than both sides
FRAME_COVERAGE = 0.5  # share of the frame's rows a panel border must run along
PANEL_COVERAGE = 0.8  # share of the panel a border or crosshair line must run along


def _peaks(profile: np.ndarray, threshold: float) -> list[int]:
    """Index of the strongest value in each run of values above threshold."""
    idx = np.where(profile >= threshold)[0]
    if not len(idx):
        return []
    runs = np.split(idx, np.where(np.diff(idx) > 2)[0] + 1)
    return [int(run[profile[run].argmax()]) for run in runs]


def find_map(gray: np.ndarray) -> tuple[Rect, Pixel | None] | None:
    """(panel, crosshair) or None when no map is open. Both are drawn as bright
    1-2 px lines: the panel border is the outermost pair, the crosshair the pair
    inside it (None when the mouse is off the map)."""
    reach = RIDGE_REACH
    g = gray.astype(np.int16)
    sides = np.maximum(g[:, : -2 * reach], g[:, 2 * reach :])
    ridge_v = (g[:, reach:-reach] - sides) > RIDGE_CONTRAST  # brighter than left and right
    above_below = np.maximum(g[: -2 * reach], g[2 * reach :])
    ridge_h = (g[reach:-reach] - above_below) > RIDGE_CONTRAST

    cols = [c + reach for c in _peaks(ridge_v.mean(0), FRAME_COVERAGE)]
    if len(cols) < 2:
        return None
    left, right = cols[0], cols[-1]
    rows = [r + reach for r in _peaks(ridge_h[:, left:right].mean(1), PANEL_COVERAGE)]
    if len(rows) < 2:
        return None
    top, bottom = rows[0], rows[-1]
    cols = [c + reach for c in _peaks(ridge_v[top:bottom].mean(0), PANEL_COVERAGE)]
    inner_c = [c for c in cols if left + reach < c < right - reach]
    inner_r = [r for r in rows if top + reach < r < bottom - reach]
    crosshair = (inner_c[0], inner_r[0]) if inner_c and inner_r else None
    return (left, top, right, bottom), crosshair
