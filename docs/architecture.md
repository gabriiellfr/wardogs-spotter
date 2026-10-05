# Architecture

## The flow

```
capture/            vision/            tracking/         ui/
frames  ----------> MapTracker ------> MapState -------> HudModel --> HudPainter
(window or replay)  one reading        position, target, plain        overlay,
                    per frame          solution          values       preview,
                                                                      screenshots
```

Data moves left to right and each stage depends only on the ones to its left:

| Package | Knows about | Does not know about |
| --- | --- | --- |
| `vision` | numpy, OpenCV | threads, windows, Qt, where frames come from |
| `ballistics` | math | everything else |
| `capture` | Windows Graphics Capture, files | what is in a frame |
| `tracking` | `vision`, `ballistics`, a `FrameBuffer` | Qt, the game window |
| `ui` | Qt, `tracking`'s state | how frames are captured or read |
| `app` | all of them | |

`app.py` is the only module that names concrete classes from every package.
The others receive what they need: the watcher gets a `FrameBuffer`, the
windows get functions that return what to draw.

This is why the tests need neither the game nor a screen: `vision` runs on
image files, `tracking` on made-up readings, `ui.model` on made-up states, and
the painter on an in-memory image.

## Threads

| Thread | Runs | Shares |
| --- | --- | --- |
| Capture | Windows Graphics Capture delivers each frame; `WindowCapturer` looks for the game window and restarts the capture when it ends. | Publishes to the `FrameBuffer`. |
| Map watcher | `MapWatcher` waits for a frame newer than the last one it read, reads it, and replaces the state. | Reads the `FrameBuffer`, writes `MapState`. |
| Qt (main) | Timers: the overlay asks for the current `HudModel` 30 times a second; the hotkeys are polled every 25 ms. | Reads `MapState`. |

Two rules keep this simple:

- **Only the newest frame matters.** `FrameBuffer` holds one frame. A reader
  that falls behind skips frames instead of queueing them, so the HUD never
  has a backlog to work through.
- **Shared values are never changed in place.** A published frame is a new
  array each time. `MapState` is frozen and replaced whole. Reading the latest
  one is a single reference read, with no lock held while it is used.

## The HUD in two steps

`build_hud` turns a `MapState` into a `HudModel`: what is shown, as plain
values with no Qt in them. `HudPainter` draws a `HudModel` on any `QPainter`.

- The overlay compares each new model with the one on screen and repaints only
  when they differ. While the map is closed that is once a second at first,
  when the age of the position changes, and once a minute after the first
  minute.
- One painter serves three places: the overlay window, the preview window, and
  the copy of a screenshot saved with the HUD on it. They can't drift apart.
- What the HUD says in each situation is tested by comparing models, with no
  pixels involved.

## Choices worth knowing

**The overlay is positioned through Win32, not Qt.** The game's bounds come
from Windows in physical pixels. Qt positions windows in scaled units that
depend on each monitor's scaling. Setting the position with `SetWindowPos`
keeps both in the same units on any monitor setup.

**Hotkeys are polled, not registered.** `RegisterHotKey` takes the key away
from every other program, the game included. Reading the keyboard state leaves
the key with the game.

**The capture library is imported late.** `capture/window.py` is imported by
`app.run` only when a live capture starts, so the `read` and `learn` commands,
the replay and the tests don't need it.

**Out of memory is survived, not avoided.** With the game running, Windows can
refuse a frame-sized allocation. `OutOfMemoryGuard` turns that one failure into
a skipped frame in each place a frame is allocated, instead of a dead thread.

## Where to change what

| To | Look at |
| --- | --- |
| Support another resolution | `wardogs-spotter learn`, then the size constants at the top of `vision/labels.py` and `vision/arrow.py` |
| Add the mortar's elevation | `ballistics.py` (`FiringSolution`), then `ui/model.py` and `ui/hud.py` to show it |
| Change what the HUD looks like | `ui/theme.py` for colors and type, `ui/hud.py` for layout |
| Capture from something else | A class with a `frames` buffer, like `capture/replay.py` |
| Add a hotkey | `config.py` (`Hotkeys`) and `Spotter._poll_hotkeys` in `app.py` |
