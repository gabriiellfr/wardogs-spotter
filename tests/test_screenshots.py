import cv2
import numpy as np

from wardogs_spotter.ballistics import solve
from wardogs_spotter.screenshots import ScreenshotSaver
from wardogs_spotter.ui.hud import HudPainter
from wardogs_spotter.ui.model import Fix, HudModel

MODEL = HudModel(
    fix=Fix.STALE,
    position=(83.0, 73.0),
    fix_age_s=5,
    target=(85.0, 68.0),
    solution=solve((83.0, 73.0), (85.0, 68.0)),
)


def test_a_screenshot_is_saved_as_seen_and_as_captured(qapp, frames, tmp_path):
    frame = frames[3]
    saver = ScreenshotSaver(tmp_path / "shots", tmp_path / "shots" / "raw", HudPainter())

    path = saver.save(frame, 42, MODEL)

    assert path is not None and path.parent == tmp_path / "shots"
    assert path.name.startswith("live_") and path.name.endswith("_42.png")
    raw = cv2.imread(str(tmp_path / "shots" / "raw" / path.name))
    seen = cv2.imread(str(path))
    # The raw one is the capture, pixel for pixel: the reader can read it again.
    assert np.array_equal(raw, frame)
    # The one you open first has the HUD on it, and is the game everywhere else.
    assert seen.shape == frame.shape
    bar = (slice(30, 80), slice(30, 500))
    assert (seen[bar] != frame[bar]).any()
    assert np.array_equal(seen[300:, 600:], frame[300:, 600:])


def test_a_folder_that_cannot_be_written_gives_no_screenshot(qapp, frames, tmp_path):
    blocker = tmp_path / "shots"
    blocker.write_text("a file where the folder should be")
    saver = ScreenshotSaver(blocker, blocker / "raw", HudPainter())
    assert saver.save(frames[0], 1, MODEL) is None  # reported, not raised: the HUD keeps running
    assert blocker.read_text() == "a file where the folder should be"
