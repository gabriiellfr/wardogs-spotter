"""Settings a run is started with. Tuning of the map reader lives next to the
code it tunes, in wardogs_spotter.vision."""

from dataclasses import dataclass, field
from pathlib import Path

VK_F8, VK_F9 = 0x77, 0x78  # Windows virtual-key codes


@dataclass(frozen=True)
class GameWindow:
    """How the game's window is recognized."""

    title: str = "Wardogs"
    window_class: str = "UnrealWindow"


@dataclass(frozen=True)
class Hotkeys:
    """Virtual-key codes, read from the keyboard state while you play."""

    screenshot: int = VK_F8
    toggle_hud: int = VK_F9


@dataclass(frozen=True)
class Settings:
    game: GameWindow = field(default_factory=GameWindow)
    hotkeys: Hotkeys = field(default_factory=Hotkeys)
    screenshots_dir: Path = Path("screenshots")  # screenshots as seen, with the HUD
    hud_fps: int = 30  # how often the HUD checks for something new to draw
    hud_scale: float = 1.0  # size of the HUD bar and its text
    fps_window: int = 60  # frames the capture rate is averaged over

    @property
    def raw_screenshots_dir(self) -> Path:
        """Where the game's own image of each screenshot goes, without the
        HUD: what the `read` command and `--replay` take."""
        return self.screenshots_dir / "raw"
