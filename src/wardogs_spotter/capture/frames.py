"""The newest frame, shared between the thread that produces frames and the
threads that read them."""

import threading
import time
from collections import deque
from dataclasses import dataclass
from typing import Protocol

import numpy as np


class RateMeter:
    """Events per second over the last `window` events."""

    def __init__(self, window: int = 60) -> None:
        self._stamps: deque[float] = deque(maxlen=window)

    def tick(self, now: float) -> None:
        self._stamps.append(now)

    def rate(self, now: float) -> float:
        """Decays to 0 when the events stop."""
        if len(self._stamps) < 2 or now <= self._stamps[0]:
            return 0.0
        return (len(self._stamps) - 1) / (now - self._stamps[0])


@dataclass(frozen=True)
class Snapshot:
    frame: np.ndarray | None  # newest BGR frame; None until the first arrives
    count: int  # frames published so far: a different count means a different frame
    fps: float  # rate the frames are arriving at


class FrameBuffer:
    """Holds the newest frame. Readers never see a frame being written: each
    published frame is a new array, and readers must not change it."""

    def __init__(self, fps_window: int = 60) -> None:
        self._changed = threading.Condition()
        self._frame: np.ndarray | None = None
        self._count = 0
        self._arrivals = RateMeter(fps_window)

    def publish(self, frame: np.ndarray) -> None:
        with self._changed:
            self._frame = frame
            self._count += 1
            self._arrivals.tick(time.perf_counter())
            self._changed.notify_all()

    def snapshot(self) -> Snapshot:
        with self._changed:
            return Snapshot(self._frame, self._count, self._arrivals.rate(time.perf_counter()))

    def wait_newer(self, count: int, timeout: float) -> Snapshot:
        """Block until a frame other than number `count` is there, or timeout
        seconds pass, and return the newest either way."""
        with self._changed:
            self._changed.wait_for(lambda: self._count != count, timeout)
        return self.snapshot()


class FrameSource(Protocol):
    """Anything that fills a FrameBuffer on a thread of its own."""

    frames: FrameBuffer

    @property
    def hwnd(self) -> int | None:
        """The window the frames come from, to put the HUD over; None while
        there is none."""

    def status(self) -> str | None:
        """Why no frames are coming, for the user to read; None when they are."""

    def start(self) -> None: ...

    def stop(self) -> None: ...

    def join(self, timeout: float | None = None) -> None: ...
