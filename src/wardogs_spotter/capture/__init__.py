"""Where frames come from.

    frames  the newest frame, shared between threads, and the FrameSource protocol
    window  the game window, through Windows Graphics Capture
    replay  saved screenshots, played in a loop

`window` needs Windows and is imported only by the code that starts a capture.
"""

from wardogs_spotter.capture.frames import FrameBuffer, FrameSource, RateMeter, Snapshot

__all__ = ["FrameBuffer", "FrameSource", "RateMeter", "Snapshot"]
