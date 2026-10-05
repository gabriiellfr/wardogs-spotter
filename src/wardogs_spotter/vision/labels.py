"""Read the coordinates the game prints next to the crosshair.

Characters are read by comparing them with glyphs cut from real screenshots
(assets/glyphs/<char>/), since the game's font never changes. They were cut at
1920x1080; another resolution needs glyphs learned at that resolution.
"""

import re
from pathlib import Path

import cv2
import numpy as np

from wardogs_spotter.geometry import Box, Pixel
from wardogs_spotter.vision.reading import LabelLine

GLYPHS_DIR = Path(__file__).resolve().parent.parent / "assets" / "glyphs"
GLYPH_SIZE = (9, 13)  # (w, h) window around each glyph's center that is compared
MAX_GLYPH_W = 11  # px; wider blobs are two touching glyphs
MAX_GLYPH_H = 18  # px; taller blobs are not text
MIN_LINE_GLYPHS = 5  # the shortest label, like "x9.99", has five
LABEL = re.compile(r"^([xy])(\d{1,3}\.\d\d)$")
SEARCH_X, SEARCH_Y = 150, 95  # px around the crosshair where the labels are printed
MIN_MATCH = 0.5  # a glyph that matches nothing better than this reads as "?"

THIN = cv2.getStructuringElement(cv2.MORPH_RECT, (7, 7))  # wider than text strokes


def _text_lines(gray: np.ndarray, crosshair: Pixel) -> tuple[list[list[Box]], np.ndarray, Pixel]:
    """(lines of glyph boxes near the crosshair, the image of bright thin
    strokes they were found in, that image's origin in the frame)."""
    cx, cy = crosshair
    x0, y0 = max(cx - SEARCH_X, 0), max(cy - SEARCH_Y, 0)
    window = gray[y0 : cy + SEARCH_Y, x0 : cx + SEARCH_X]
    hat = cv2.morphologyEx(window, cv2.MORPH_TOPHAT, THIN)
    hat[:, max(cx - x0 - 2, 0) : cx - x0 + 3] = 0  # the crosshair is a bright thin stroke too
    hat[max(cy - y0 - 2, 0) : cy - y0 + 3, :] = 0
    thr = max(25.0, 0.45 * np.percentile(hat, 99.9))  # relative: some labels are dimmer
    ink = (hat > thr).astype(np.uint8)
    _, _, stats, _ = cv2.connectedComponentsWithStats(ink, connectivity=8)
    boxes: list[Box] = []
    for x, y, w, h, area in stats[1:]:
        if h > MAX_GLYPH_H or w > 2 * MAX_GLYPH_W + 2 or area < 2:
            continue
        if w > MAX_GLYPH_W:  # two glyphs touching, like "y7": cut at the thinnest middle column
            columns = (hat[y : y + h, x : x + w] > thr).sum(0)
            cut = int(np.argmin(columns[w // 3 : w - w // 3])) + w // 3
            boxes += [(x, y, cut, h), (x + cut, y, w - cut, h)]
        else:
            boxes.append((x, y, w, h))

    lines: list[list[Box]] = []
    for b in sorted(boxes):
        for line in lines:
            top = min(q[1] for q in line)
            bottom = max(q[1] + q[3] for q in line)
            last = line[-1]
            overlap = min(bottom, b[1] + b[3]) - max(top, b[1])
            gap = b[0] - (last[0] + last[2])
            if overlap >= 0.6 * min(b[3], bottom - top) and -1 <= gap <= 5:
                line.append(b)
                break
        else:
            lines.append([b])
    in_frame = [
        [(int(x + x0), int(y + y0), int(w), int(h)) for x, y, w, h in line]
        for line in lines
        if len(line) >= MIN_LINE_GLYPHS
    ]
    return in_frame, hat, (x0, y0)


def _glyph(hat: np.ndarray, box: Box, origin: Pixel, pad: int = 0) -> np.ndarray:
    """GLYPH_SIZE window centered on the box, plus pad px on every side. A fixed
    window keeps the shape intact when a faint edge falls outside the box."""
    x, y, w, h = box
    gw, gh = GLYPH_SIZE
    left = x - origin[0] + (w - gw) // 2 - pad
    top = y - origin[1] + (h - gh) // 2 - pad
    padded = cv2.copyMakeBorder(hat, gh, gh, gw, gw, cv2.BORDER_CONSTANT)
    window = padded[top + gh : top + gh + gh + 2 * pad, left + gw : left + gw + gw + 2 * pad]
    return window.astype(np.float32)


def _norm(patch: np.ndarray) -> np.ndarray:
    """The patch as a unit vector, so a dot product of two is their correlation."""
    patch = patch.ravel() - patch.mean()
    unit: np.ndarray = patch / (np.linalg.norm(patch) + 1e-6)
    return unit


class GlyphReader:
    """Names each glyph after the character whose closest learned examples
    match it best."""

    def __init__(self, folder: Path = GLYPHS_DIR) -> None:
        self.folder = folder
        chars, widths, patches = [], [], []
        for path in sorted(folder.glob("*/*.png")):  # named <width>_<n>.png
            image = cv2.imread(str(path), cv2.IMREAD_GRAYSCALE)
            if image is None:
                raise ValueError(f"{path} is not an image")
            chars.append(path.parent.name)
            widths.append(int(path.stem.split("_")[0]))
            patches.append(_norm(image.astype(np.float32)))
        self.chars = np.array(chars)
        self.widths = np.array(widths)
        self.patches = np.array(patches, np.float32).reshape(
            len(patches), GLYPH_SIZE[0] * GLYPH_SIZE[1]
        )

    def name(self, hat: np.ndarray, box: Box, origin: Pixel) -> str:
        """The character in the box, or "?" when nothing learned resembles it."""
        _, _, w, h = box
        if w <= 4 and h <= 4:
            return "."
        gw, gh = GLYPH_SIZE
        around = _glyph(hat, box, origin, pad=1)
        shifted = np.array(
            [_norm(around[dy : dy + gh, dx : dx + gw]) for dy in range(3) for dx in range(3)]
        )
        scores = (shifted @ self.patches.T).max(0)  # best of the 1 px shifts
        scores -= 0.05 * np.maximum(0, np.abs(self.widths - w) - 1)
        best, best_score = "?", MIN_MATCH
        for char in np.unique(self.chars):
            # The mean of the top three: one odd example can't win alone.
            score = np.sort(scores[self.chars == char])[-3:].mean()
            if score > best_score:
                best, best_score = str(char), score
        return best

    def read(self, gray: np.ndarray, crosshair: Pixel) -> tuple[dict[str, float], list[LabelLine]]:
        """{'x': value, 'y': value} printed at the crosshair, plus the lines read."""
        lines, hat, origin = _text_lines(gray, crosshair)
        values: dict[str, float] = {}
        read: list[LabelLine] = []
        for line in lines:
            text = "".join(self.name(hat, box, origin) for box in line)
            read.append((text, line))
            match = LABEL.match(text)
            if match and match.group(1) not in values:
                values[match.group(1)] = float(match.group(2))
        return values, read

    def learn(self, gray: np.ndarray, crosshair: Pixel, labels: list[str]) -> int:
        """Save the glyphs of the lines that have exactly as many glyphs as
        the labels, given top to bottom. Returns how many labels were used."""
        lines, hat, origin = _text_lines(gray, crosshair)
        lines.sort(key=lambda line: line[0][1])
        used = 0
        for label in labels:
            line = next((ln for ln in lines if len(ln) == len(label)), None)
            if line is None:
                continue
            lines.remove(line)
            used += 1
            for char, box in zip(label, line, strict=True):
                if char == ".":
                    continue
                folder = self.folder / char
                folder.mkdir(parents=True, exist_ok=True)
                name = f"{box[2]}_{len(list(folder.glob('*.png')))}.png"
                cv2.imwrite(str(folder / name), _glyph(hat, box, origin).astype(np.uint8))
        return used
