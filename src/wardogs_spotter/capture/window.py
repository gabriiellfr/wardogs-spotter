"""Capture the game window, the way OBS's Window Capture does.

Frames come from Windows Graphics Capture (WGC), the API behind OBS's
"Windows 10 (1903 and up)" capture method: Windows hands over the window's own
image from the compositor, so the game is captured even when other windows
cover it, and the HUD drawn over the game is never part of the frames. A
minimized window sends no frames until it is restored.

The game does not have to be running at start: its window is looked up every
second, and found again when the game restarts.
"""

import logging
import threading
from typing import Any

import cv2
from windows_capture import WindowsCapture

from wardogs_spotter import winapi
from wardogs_spotter.capture.frames import FrameBuffer
from wardogs_spotter.config import GameWindow
from wardogs_spotter.memory import OutOfMemoryGuard

log = logging.getLogger(__name__)

FIND_EVERY = 1.0  # seconds between looking for the game window


class WindowCapturer(threading.Thread):
    """Waits for the game window, captures it with WGC and publishes every
    frame. When the game closes it goes back to waiting."""

    def __init__(self, game: GameWindow, fps_window: int = 60) -> None:
        super().__init__(name="capture", daemon=True)
        self.frames = FrameBuffer(fps_window)
        self._game = game
        self._stopping = threading.Event()
        self._hwnd: int | None = None

    @property
    def hwnd(self) -> int | None:
        """The window being captured; None while waiting for the game."""
        return self._hwnd

    def status(self) -> str | None:
        hwnd = self._hwnd
        if hwnd is None:
            return f"Waiting for {self._game.title} to start"
        if winapi.is_minimized(hwnd):
            return f"{self._game.title} is minimized"
        return None

    def stop(self) -> None:
        self._stopping.set()

    def run(self) -> None:
        title = self._game.title
        while not self._stopping.is_set():
            hwnd = winapi.find_window(title, self._game.window_class)
            if hwnd is None:
                self._stopping.wait(FIND_EVERY)
                continue
            log.info("Capturing %s (window %s)", title, hwnd)
            self._hwnd = hwnd
            control = self._capture(hwnd)
            # The capture ends by itself when the game window closes.
            while not control.is_finished():
                if self._stopping.wait(0.1):
                    control.stop()
                    break
            self._hwnd = None
            if self._stopping.is_set():
                break
            if winapi.is_window(hwnd):  # the capture failed, not the game
                log.warning("Capture stopped; starting it again")
                self._stopping.wait(FIND_EVERY)
            else:
                log.info("%s closed, waiting for it to start again", title)

    def _capture(self, hwnd: int) -> Any:
        """Start a WGC session on the window and return its control; frames
        arrive on its own thread, which also keeps it clear of COM set up on
        ours."""
        # A 1 ms minimum interval lets every frame the game draws through
        # (Windows 11 24H2 and later); the default dropped some.
        capture = WindowsCapture(
            cursor_capture=False, draw_border=False, minimum_update_interval=1, window_hwnd=hwnd
        )

        @capture.event
        def on_frame_arrived(frame: Any, control: Any) -> None:
            # frame_buffer is mapped GPU memory, valid only during this call,
            # so the conversion doubles as the copy. An exception here would
            # end the capture: out of memory skips the frame instead.
            with OutOfMemoryGuard() as guard:
                bgr = cv2.cvtColor(frame.frame_buffer, cv2.COLOR_BGRA2BGR)
            if not guard.tripped:
                self.frames.publish(bgr)

        @capture.event
        def on_closed() -> None:
            pass  # run() notices through is_finished()

        return capture.start_free_threaded()
