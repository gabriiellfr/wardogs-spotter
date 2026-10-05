# Changelog

The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and the versions follow [Semantic Versioning](https://semver.org/).

## [0.1.0] - 2026-10-05

The first public version.

### Added

- Capture of the game window through Windows Graphics Capture. The game is
  found by its window and found again when it restarts.
- A map reader: finds the map panel and the crosshair, reads the coordinates
  printed at the cursor, finds the player's arrow and its heading.
- A tracker that follows the map through pans and zooms to work out its scale,
  and with it the player's coordinates.
- Range and azimuth from the player to the last point the mouse was on, kept
  after the map closes.
- A HUD drawn over the game in a transparent, click-through window: a bar with
  the solution and both sets of coordinates, a ring on the player's arrow, and
  a line to the cursor with the solution next to it.
- A tray icon to hide the HUD, save a screenshot, open the screenshots folder
  and quit.
- Hotkeys that work while the game has the focus: `F8` saves a screenshot,
  `F9` hides or shows the HUD.
- `preview`: the capture in a window with the HUD and the reader's numbers,
  live or replaying saved screenshots.
- `read`: reads saved screenshots and saves copies with the reading marked.
- `learn`: teaches the reader the characters of a screenshot.
- A Windows executable attached to each release, so the program runs without
  installing Python.

[0.1.0]: https://github.com/gabriiellfr/wardogs-spotter/releases/tag/v0.1.0
