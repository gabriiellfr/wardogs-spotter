"""Work on saved screenshots, without the game: read them to check the reader
by eye, or teach it the glyphs of a screenshot it can't read."""

from pathlib import Path

import cv2

from wardogs_spotter.vision import GlyphReader, MapTracker, describe, draw, find_map

MARKED = "read"  # subfolder for the copies with the reading marked on them


def read_screenshots(paths: list[Path]) -> int:
    """Read the screenshots in order, as the frames of one session, print what
    each one gave and save a marked copy next to the first. Returns how many
    showed an open map."""
    tracker = MapTracker()
    out = paths[0].parent / MARKED
    out.mkdir(exist_ok=True)
    read = 0
    for path in paths:
        frame = cv2.imread(str(path))
        if frame is None:
            print(f"{path.name}: not an image")
            continue
        reading = tracker.update(frame)
        if reading is None:
            print(f"{path.name}: no map open")
            continue
        read += 1
        print(f"{path.name}: {describe(reading)}")
        cv2.imwrite(str(out / path.name), draw(frame, reading))
    print(f"Marked copies are in {out}")
    return read


def learn_glyphs(paths: list[Path], labels: list[str]) -> None:
    """Cut the glyphs of each screenshot's coordinate labels and add them to
    the ones the reader knows. `labels` are the texts on screen, top to
    bottom, like ["y109.58", "x99.23"]."""
    glyphs = GlyphReader()
    for path in paths:
        frame = cv2.imread(str(path))
        if frame is None:
            print(f"{path.name}: not an image")
            continue
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        found = find_map(gray)
        crosshair = found[1] if found else None
        used = glyphs.learn(gray, crosshair, labels) if crosshair else 0
        print(f"{path.name}: learned {used} of {len(labels)} labels")
