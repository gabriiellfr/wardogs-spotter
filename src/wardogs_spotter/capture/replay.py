"""Play saved screenshots as if they were being captured.

The program without the game: for trying the map reader and the HUD on frames
saved with the screenshot hotkey, and for working on the code away from it.
"""

import logging
import threading
from pathlib import Path

import cv2

from wardogs_spotter.capture.frames import FrameBuffer

log = logging.getLogger(__name__)


class ReplaySource(threading.Thread):
    """Publishes the screenshots in order, each for `hold` seconds, in a loop."""

    def __init__(self, paths: list[Path], hold: float = 1.5, fps_window: int = 60) -> None:
        super().__init__(name="replay", daemon=True)
        self.frames = FrameBuffer(fps_window)
        self._paths = paths
        self._hold = hold
        self._stopping = threading.Event()

    @property
    def hwnd(self) -> None:
        """A replay has no window to put the HUD over."""
        return None

    def status(self) -> str | None:
        return f"Replaying {len(self._paths)} screenshots"

    def stop(self) -> None:
        self._stopping.set()

    def run(self) -> None:
        while not self._stopping.is_set():
            shown = 0
            for path in self._paths:  # read one at a time: a frame is several MB
                frame = cv2.imread(str(path))
                if frame is None:
                    log.warning("%s is not an image, skipping it", path)
                    continue
                self.frames.publish(frame)
                shown += 1
                if self._stopping.wait(self._hold):
                    return
            if not shown:
                log.error("None of the screenshots could be read")
                return
