"""Read the map from frames as they arrive, on a thread of its own."""

import threading
import time

from wardogs_spotter.capture.frames import FrameBuffer
from wardogs_spotter.memory import OutOfMemoryGuard
from wardogs_spotter.tracking.state import MapState, advance
from wardogs_spotter.vision import MapTracker

OUT_OF_MEMORY_PAUSE = 0.5  # seconds; gives Windows a moment before the next frame


class MapWatcher(threading.Thread):
    """Reads the in-game map from the newest frame, skipping the frames it
    can't keep up with, and keeps the resulting MapState."""

    def __init__(self, frames: FrameBuffer, tracker: MapTracker | None = None) -> None:
        super().__init__(name="map-watcher", daemon=True)
        self._frames = frames
        self._tracker = tracker or MapTracker()
        self._stopping = threading.Event()
        self._state = MapState()

    @property
    def state(self) -> MapState:
        """The latest state. Safe to read from any thread: states are immutable
        and replacing the reference is atomic."""
        return self._state

    def stop(self) -> None:
        self._stopping.set()

    def run(self) -> None:
        count = 0
        while not self._stopping.is_set():
            snapshot = self._frames.wait_newer(count, timeout=0.1)
            frame = snapshot.frame
            if snapshot.count == count or frame is None:
                continue
            count = snapshot.count
            started = time.perf_counter()
            with OutOfMemoryGuard() as guard:
                reading = self._tracker.update(frame)
            if guard.tripped:
                self._stopping.wait(OUT_OF_MEMORY_PAUSE)
                continue
            now = time.perf_counter()
            height, width = frame.shape[:2]
            self._state = advance(
                self._state, reading, now, (now - started) * 1000, (width, height)
            )
