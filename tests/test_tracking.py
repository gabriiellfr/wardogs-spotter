import threading

import numpy as np
import pytest

from wardogs_spotter.capture import FrameBuffer, RateMeter
from wardogs_spotter.tracking import MapState, MapWatcher, PlayerFix, Target, advance
from wardogs_spotter.vision import MapReading

PANEL = (0, 0, 700, 700)


def reading(cursor=None, player_coords=None, heading=None) -> MapReading:
    return MapReading(
        PANEL,
        crosshair=(300, 300) if cursor else None,
        cursor=cursor,
        player=(400, 400) if heading is not None else None,
        heading=heading,
        player_coords=player_coords,
    )


def test_nothing_is_known_at_first():
    state = MapState()
    assert state.player is None and state.target is None
    assert state.solution is None and state.aim is None


def test_the_cursor_becomes_the_target():
    state = advance(MapState(), reading(cursor=(80.0, 70.0)), now=5.0)
    assert state.target == Target((80.0, 70.0), 5.0)
    assert state.solution is None  # no position yet


def test_a_reading_with_coordinates_fixes_the_player():
    state = advance(MapState(), reading(player_coords=(83.0, 73.0), heading=90), now=5.0)
    assert state.player == PlayerFix((83.0, 73.0), 90, 5.0)


def test_the_cursor_on_the_players_arrow_is_not_a_target():
    on_arrow = reading(cursor=(83.0, 73.0), player_coords=(83.0, 73.0), heading=90)
    state = advance(MapState(), on_arrow, now=5.0)
    assert state.player is not None
    assert state.target is None
    assert state.aim is None


def test_position_and_target_outlive_the_map():
    state = advance(MapState(), reading((80.0, 70.0), (83.0, 73.0), heading=90), now=5.0)
    closed = advance(state, None, now=60.0)
    assert closed.reading is None
    assert closed.player == state.player and closed.target == state.target
    assert closed.solution == state.solution
    assert closed.aim is None  # nothing is under the cursor with the map closed


def test_the_solution_runs_from_the_player_to_the_target():
    state = advance(MapState(), reading((83.0, 78.0), (83.0, 73.0), heading=0), now=5.0)
    assert state.solution.distance_m == pytest.approx(500)
    assert state.solution.azimuth_deg == pytest.approx(0)
    assert state.aim == state.solution


def test_a_frame_without_news_keeps_what_was_known():
    state = advance(MapState(), reading((80.0, 70.0), (83.0, 73.0), heading=90), now=5.0)
    later = advance(state, reading(), now=6.0)
    assert later.player == state.player and later.target == state.target


def test_rate_meter():
    meter = RateMeter(window=4)
    assert meter.rate(0.0) == 0
    for stamp in (0.0, 0.1, 0.2, 0.3):
        meter.tick(stamp)
    assert meter.rate(0.3) == pytest.approx(10)
    assert meter.rate(3.0) == pytest.approx(1)  # decays once the events stop


def test_frame_buffer_hands_out_the_newest_frame():
    frames = FrameBuffer()
    assert frames.snapshot().frame is None
    first, second = np.zeros((2, 2, 3), np.uint8), np.ones((2, 2, 3), np.uint8)
    frames.publish(first)
    frames.publish(second)
    snapshot = frames.snapshot()
    assert snapshot.frame is second and snapshot.count == 2


def test_frame_buffer_wakes_a_waiting_reader():
    frames = FrameBuffer()
    assert frames.wait_newer(0, timeout=0.01).count == 0  # nothing came: times out
    threading.Timer(0.05, frames.publish, [np.zeros((2, 2, 3), np.uint8)]).start()
    assert frames.wait_newer(0, timeout=5).count == 1


class ScriptedTracker:
    """Stands in for MapTracker: gives one prepared reading per frame."""

    def __init__(self, readings):
        self._readings = iter(readings)
        self.done = threading.Event()

    def update(self, frame):
        value = next(self._readings)
        self.done.set()
        return value


def test_watcher_reads_published_frames_into_the_state():
    frames = FrameBuffer()
    tracker = ScriptedTracker([reading((80.0, 70.0), (83.0, 73.0), heading=90)])
    watcher = MapWatcher(frames, tracker)
    watcher.start()
    try:
        frames.publish(np.zeros((1080, 1920, 3), np.uint8))
        assert tracker.done.wait(5)
        for _ in range(500):  # the state is swapped in right after the read
            if watcher.state.frame_size:
                break
            threading.Event().wait(0.01)
        state = watcher.state
        assert state.frame_size == (1920, 1080)
        assert state.player.coords == (83.0, 73.0)
        assert state.target.coords == (80.0, 70.0)
    finally:
        watcher.stop()
        watcher.join(5)
    assert not watcher.is_alive()
