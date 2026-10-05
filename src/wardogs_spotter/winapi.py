"""The few Win32 calls the program needs, declared once.

Nothing here touches the game's process: no injection, no process handle, no
memory reads. The game is found by its window (class and title), and only
window-level facts are read: its bounds, whether it is minimized, whether it
is the foreground window.
"""

import ctypes
from ctypes import wintypes

from wardogs_spotter.geometry import Rect

_HWND_TOPMOST = wintypes.HWND(-1)
_SWP_NOACTIVATE = 0x10
_DWMWA_EXTENDED_FRAME_BOUNDS = 9

_user32 = ctypes.WinDLL("user32", use_last_error=True)
_dwmapi = ctypes.WinDLL("dwmapi")

_WNDENUMPROC = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)
_user32.EnumWindows.argtypes = [_WNDENUMPROC, wintypes.LPARAM]
for _name in ("IsWindow", "IsWindowVisible", "IsIconic"):
    getattr(_user32, _name).argtypes = [wintypes.HWND]
_user32.GetClassNameW.argtypes = [wintypes.HWND, wintypes.LPWSTR, ctypes.c_int]
_user32.GetWindowTextW.argtypes = [wintypes.HWND, wintypes.LPWSTR, ctypes.c_int]
_user32.GetForegroundWindow.restype = wintypes.HWND
_user32.GetAsyncKeyState.argtypes = [ctypes.c_int]
_user32.GetAsyncKeyState.restype = ctypes.c_short
_user32.SetWindowPos.argtypes = [
    wintypes.HWND, wintypes.HWND, ctypes.c_int, ctypes.c_int, ctypes.c_int, ctypes.c_int,
    wintypes.UINT,
]  # fmt: skip
_dwmapi.DwmGetWindowAttribute.argtypes = [
    wintypes.HWND, wintypes.DWORD, ctypes.c_void_p, wintypes.DWORD,
]  # fmt: skip


def find_window(title: str, window_class: str) -> int | None:
    """Handle of the visible window with this class and title, or None.
    Only the window is looked at, never the process behind it."""
    found: list[int] = []

    def visit(hwnd: int, _: int) -> bool:
        cls = ctypes.create_unicode_buffer(64)
        text = ctypes.create_unicode_buffer(64)
        _user32.GetClassNameW(hwnd, cls, len(cls))
        _user32.GetWindowTextW(hwnd, text, len(text))
        if (
            _user32.IsWindowVisible(hwnd)
            and cls.value == window_class
            and text.value.strip() == title
        ):
            found.append(hwnd)
            return False  # stop enumerating
        return True

    _user32.EnumWindows(_WNDENUMPROC(visit), 0)
    return found[0] if found else None


def is_window(hwnd: int) -> bool:
    """False once the window was destroyed."""
    return bool(_user32.IsWindow(hwnd))


def is_minimized(hwnd: int) -> bool:
    return bool(_user32.IsIconic(hwnd))


def foreground_window() -> int | None:
    """Handle of the window the user is working in."""
    hwnd: int | None = _user32.GetForegroundWindow()
    return hwnd


def window_bounds(hwnd: int) -> Rect:
    """(left, top, right, bottom) of the window as drawn on screen, in physical
    pixels: the area Windows Graphics Capture captures (no invisible resize
    borders)."""
    rect = wintypes.RECT()
    _dwmapi.DwmGetWindowAttribute(
        hwnd, _DWMWA_EXTENDED_FRAME_BOUNDS, ctypes.byref(rect), ctypes.sizeof(rect)
    )
    return rect.left, rect.top, rect.right, rect.bottom


def place_topmost(hwnd: int, bounds: Rect) -> None:
    """Move the window over bounds (physical pixels) and above every other
    window, topmost ones included, without giving it the focus."""
    left, top, right, bottom = bounds
    _user32.SetWindowPos(
        hwnd, _HWND_TOPMOST, left, top, right - left, bottom - top, _SWP_NOACTIVATE
    )


def key_down(virtual_key: int) -> bool:
    """Whether the key is held right now. Like OBS hotkeys, the key is read
    from the keyboard state rather than grabbed, so it works whichever window
    has focus and the game still gets it."""
    return bool(_user32.GetAsyncKeyState(virtual_key) < 0)
