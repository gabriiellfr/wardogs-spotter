"""Keep running when Windows runs out of memory.

The game can leave Windows with almost nothing to hand out. numpy and OpenCV
then fail to allocate a frame; skipping that frame keeps every thread alive
until Windows has memory again.
"""

import logging
import time
from types import TracebackType

import cv2

log = logging.getLogger(__name__)

WARN_EVERY = 10.0  # seconds between warnings
_CV_NO_MEMORY = -4  # cv::Error::StsNoMem

_last_warning = float("-inf")


def is_out_of_memory(error: BaseException) -> bool:
    """True when error is Windows refusing memory, as numpy or OpenCV report it."""
    if isinstance(error, MemoryError):
        return True
    return isinstance(error, cv2.error) and getattr(error, "code", None) == _CV_NO_MEMORY


def _warn() -> None:
    global _last_warning
    now = time.perf_counter()
    if now - _last_warning > WARN_EVERY:
        _last_warning = now
        log.warning(
            "Windows is out of memory: skipping frames until it frees some "
            "(closing other programs helps)"
        )


class OutOfMemoryGuard:
    """Context manager that swallows an out-of-memory error from numpy or
    OpenCV (anything else propagates), warns at most every WARN_EVERY seconds,
    and records what happened in `tripped`:

        with OutOfMemoryGuard() as guard:
            image = cv2.cvtColor(frame, cv2.COLOR_BGRA2BGR)
        if guard.tripped:
            return  # skip this frame
    """

    def __init__(self) -> None:
        self.tripped = False

    def __enter__(self) -> "OutOfMemoryGuard":
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        traceback: TracebackType | None,
    ) -> bool:
        if exc is None or not is_out_of_memory(exc):
            return False
        self.tripped = True
        _warn()
        return True
