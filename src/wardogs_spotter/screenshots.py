"""Save the frame on screen: as it looked, and as the reader got it."""

import logging
import time
from pathlib import Path

import cv2
import numpy as np

from wardogs_spotter.memory import OutOfMemoryGuard
from wardogs_spotter.ui.hud import HudPainter
from wardogs_spotter.ui.images import compose
from wardogs_spotter.ui.model import HudModel

log = logging.getLogger(__name__)


class ScreenshotSaver:
    """Writes each frame twice, under the same name: the screen as you saw it,
    with the HUD, to `folder`; and the game's own image to `raw_folder`.

    The second one is what the `read` command and `--replay` need. It can't be
    recovered from the first: the capture never contains the HUD, and a
    picture with the HUD on it would have its marks read as part of the map."""

    def __init__(
        self, folder: Path, raw_folder: Path, hud: HudPainter, hud_scale: float = 1.0
    ) -> None:
        self.folder = folder
        self.raw_folder = raw_folder
        self._hud = hud
        self._hud_scale = hud_scale

    def save(self, frame: np.ndarray, count: int, model: HudModel) -> Path | None:
        """Save frame number `count` with `model` drawn on it. Returns the
        path of the picture with the HUD, or None when it could not be
        written."""
        name = f"live_{time.strftime('%Y%m%d_%H%M%S')}_{count}.png"
        path, raw_path = self.folder / name, self.raw_folder / name
        saved = False
        try:
            with OutOfMemoryGuard() as guard:
                self.folder.mkdir(parents=True, exist_ok=True)
                self.raw_folder.mkdir(parents=True, exist_ok=True)
                saved = cv2.imwrite(str(raw_path), frame) and compose(
                    frame, self._hud, model, self._hud_scale
                ).save(str(path))
        except OSError as error:  # the folder can't be made: a file in its place, no rights
            log.error("Screenshot %s not saved: %s", name, error)
            return None
        if guard.tripped:
            log.error("Screenshot %s not saved: Windows is out of memory", name)
            return None
        if not saved:
            log.error("Screenshot %s could not be written", path)
            return None
        log.info("Saved %s (the game's own image is in %s)", path, self.raw_folder)
        return path
