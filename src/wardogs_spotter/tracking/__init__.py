"""What the program knows, kept up to date as frames arrive.

state    the player's last known position, the target and the firing solution
watcher  the thread that reads each new frame into the state
"""

from wardogs_spotter.tracking.state import MapState, PlayerFix, Target, advance
from wardogs_spotter.tracking.watcher import MapWatcher

__all__ = ["MapState", "MapWatcher", "PlayerFix", "Target", "advance"]
