"""Hotkeys that work while the game has the focus."""

from wardogs_spotter import winapi


class Hotkey:
    """A key watched by polling the keyboard state. Nothing is registered with
    Windows and nothing is intercepted, so the game still gets the key."""

    def __init__(self, virtual_key: int) -> None:
        self._virtual_key = virtual_key
        self._down = False

    def pressed(self) -> bool:
        """True once per press: on the first poll that finds the key down."""
        was_down, self._down = self._down, winapi.key_down(self._virtual_key)
        return self._down and not was_down
