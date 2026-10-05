"""Put the parts together and run them.

    frames (capture or replay) -> MapWatcher -> MapState -> HudModel -> HudPainter
         capture thread          reader thread            Qt thread

Nothing below this module knows about the others it is wired to: the reader
gets a FrameBuffer, the windows get callables that return what to draw.
"""

import logging
import signal
import sys
import time
from pathlib import Path

from PySide6.QtCore import QObject, QTimer, QUrl
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import QApplication

from wardogs_spotter.capture.frames import FrameSource
from wardogs_spotter.capture.replay import ReplaySource
from wardogs_spotter.config import Settings
from wardogs_spotter.geometry import format_coords
from wardogs_spotter.hotkeys import Hotkey
from wardogs_spotter.screenshots import ScreenshotSaver
from wardogs_spotter.tracking import MapWatcher
from wardogs_spotter.ui.hud import HudPainter
from wardogs_spotter.ui.model import HudModel, Toast, build_hud
from wardogs_spotter.ui.overlay import OverlayWindow
from wardogs_spotter.ui.preview import PreviewWindow
from wardogs_spotter.ui.tray import Tray, app_icon

log = logging.getLogger(__name__)

HOTKEY_POLL_MS = 25


class Spotter(QObject):
    """One run of the program: the threads, the windows and what ties them."""

    def __init__(self, settings: Settings, source: FrameSource, preview: bool) -> None:
        super().__init__()
        self._settings = settings
        self._source = source
        self._watcher = MapWatcher(source.frames)
        self._hud = HudPainter()
        self._screenshots = ScreenshotSaver(
            settings.screenshots_dir, settings.raw_screenshots_dir, self._hud, settings.hud_scale
        )
        self._toast = Toast()
        self._screenshot_key = Hotkey(settings.hotkeys.screenshot)
        self._toggle_key = Hotkey(settings.hotkeys.toggle_hud)
        self._started_at = 0.0

        self._overlay: OverlayWindow | None = None
        self._preview: PreviewWindow | None = None
        self._tray: Tray | None = None
        if preview:
            self._preview = PreviewWindow(
                source.frames, self._hud, self.hud_model, self.stats, settings.hud_scale
            )
            self._preview.screenshot_requested.connect(self.save_screenshot)
        else:  # the game itself is the display, so the tray is the way in
            self._overlay = OverlayWindow(
                self._hud, lambda: source.hwnd, self.hud_model, settings.hud_fps, settings.hud_scale
            )
            self._tray = Tray(
                app_icon(),
                on_toggle_hud=self.set_hud_shown,
                on_screenshot=self.save_screenshot,
                on_open_screenshots=self.open_screenshots,
                on_quit=QApplication.quit,
            )

        self._hotkeys = QTimer(self)
        self._hotkeys.setInterval(HOTKEY_POLL_MS)
        self._hotkeys.timeout.connect(self._poll_hotkeys)

    def start(self) -> None:
        self._started_at = time.perf_counter()
        self._source.start()
        self._watcher.start()
        self._hotkeys.start()
        if self._preview:
            self._preview.start()
        if self._overlay:
            self._overlay.start()
        if self._tray:
            self._tray.show()

    def stop(self) -> None:
        self._hotkeys.stop()
        self._source.stop()
        self._watcher.stop()
        self._source.join()
        self._watcher.join()
        if self._tray:
            self._tray.hide()
        elapsed = time.perf_counter() - self._started_at
        frames = self._source.frames.snapshot().count
        log.info("%.1f s: %d frames (%.1f fps)", elapsed, frames, frames / max(elapsed, 1e-9))

    def hud_model(self) -> HudModel:
        """What the HUD shows right now."""
        now = time.perf_counter()
        return build_hud(self._watcher.state, now, self._toast.current(now))

    def stats(self) -> list[str]:
        """What the capture and the reader are doing, for the preview."""
        snapshot = self._source.frames.snapshot()
        state = self._watcher.state
        lines = [f"Capture  {snapshot.fps:5.1f} fps"]
        if snapshot.frame is not None:
            lines.append(f"Frame    {snapshot.frame.shape[1]}x{snapshot.frame.shape[0]}")
        status = self._source.status()
        if status:
            lines.append(status)
        reading = state.reading
        lines.append(f"Map      read in {state.read_ms:.0f} ms" if reading else "Map      closed")
        if reading and reading.cursor:
            lines.append(f"Cursor   {format_coords(reading.cursor)}")
        if reading and reading.scale:
            lines.append(f"Scale    {reading.scale:.1f} px/unit")
        return lines

    def save_screenshot(self) -> None:
        snapshot = self._source.frames.snapshot()
        if snapshot.frame is None:
            return
        # Without the message about the screenshot before this one.
        model = build_hud(self._watcher.state, time.perf_counter())
        saved = self._screenshots.save(snapshot.frame, snapshot.count, model)
        message = "Screenshot saved" if saved else "Screenshot not saved"
        self._toast.show(message, time.perf_counter())

    def set_hud_shown(self, shown: bool) -> None:
        if self._overlay:
            self._overlay.enabled = shown

    def open_screenshots(self) -> None:
        folder = self._settings.screenshots_dir.resolve()
        folder.mkdir(parents=True, exist_ok=True)
        QDesktopServices.openUrl(QUrl.fromLocalFile(str(folder)))

    def _poll_hotkeys(self) -> None:
        if self._screenshot_key.pressed():
            self.save_screenshot()
        if self._toggle_key.pressed() and self._overlay and self._tray:
            self._tray.set_hud_shown(not self._overlay.enabled)  # which sets the overlay too


def run(
    settings: Settings,
    *,
    preview: bool = False,
    replay: list[Path] | None = None,
    seconds: float = 0.0,
) -> int:
    """Run until the user quits, or for `seconds`. With `replay`, the frames
    come from those screenshots instead of the game, in the preview."""
    app = QApplication(sys.argv[:1])
    app.setApplicationName("Wardogs Spotter")
    app.setWindowIcon(app_icon())
    app.setQuitOnLastWindowClosed(preview or bool(replay))

    source: FrameSource
    if replay:
        source = ReplaySource(replay, fps_window=settings.fps_window)
    else:
        # Imported here: it needs Windows Graphics Capture, the rest doesn't.
        from wardogs_spotter.capture.window import WindowCapturer

        source = WindowCapturer(settings.game, settings.fps_window)

    spotter = Spotter(settings, source, preview=preview or bool(replay))
    # Ctrl+C in the terminal. Python only notices it between Qt events, which
    # the hotkey timer provides.
    signal.signal(signal.SIGINT, lambda *_: app.quit())
    if seconds:
        QTimer.singleShot(round(seconds * 1000), app.quit)
    if not (preview or replay):
        log.info(
            "HUD on: open the map in %s. F8 saves a screenshot, F9 hides the HUD; "
            "quit from the tray icon or with Ctrl+C here.",
            settings.game.title,
        )
    spotter.start()
    try:
        return app.exec()
    finally:
        spotter.stop()
