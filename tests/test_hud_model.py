from dataclasses import replace

import pytest

from wardogs_spotter.ballistics import FiringSolution
from wardogs_spotter.tracking import MapState, PlayerFix, Target
from wardogs_spotter.ui.model import (
    HINT_FIND_ARROW,
    HINT_OPEN_MAP,
    HINT_PICK_TARGET,
    Fix,
    Toast,
    build_hud,
    format_age,
    format_azimuth,
    format_heading,
    format_range,
)
from wardogs_spotter.vision import MapReading

PANEL = (631, 208, 1288, 866)
FIX = PlayerFix((83.0, 73.0), 90, seen_at=100.0)
TARGET = Target((85.0, 68.0), seen_at=100.0)
SIZE = (1920, 1080)


def test_before_anything_is_known_it_asks_for_the_map():
    hud = build_hud(MapState(), now=0.0)
    assert hud.fix is Fix.NONE
    assert hud.hint == HINT_OPEN_MAP
    assert not hud.map_open and hud.marks is None and hud.solution is None


def test_with_the_arrow_in_sight_it_asks_for_the_mouse():
    seen = MapReading(PANEL, player=(942, 571), heading=90)
    hud = build_hud(MapState(seen, frame_size=SIZE), now=0.0)
    assert hud.map_open
    assert hud.hint == HINT_FIND_ARROW
    assert hud.marks.player == (942, 571) and hud.marks.aim is None


def test_with_a_position_and_no_target_it_asks_for_one():
    hud = build_hud(MapState(player=FIX), now=101.0)
    assert hud.hint == HINT_PICK_TARGET
    assert hud.position == (83.0, 73.0)


def test_live_while_the_frame_on_screen_gives_the_position():
    live = MapReading(
        PANEL,
        crosshair=(991, 696),
        cursor=(85.0, 68.0),
        player=(942, 571),
        heading=90,
        player_coords=(83.0, 73.0),
    )
    hud = build_hud(MapState(live, frame_size=SIZE, player=FIX, target=TARGET), now=100.0)
    assert hud.fix is Fix.LIVE
    assert hud.fix_age_s is None
    assert hud.hint is None
    assert hud.solution.distance_m == pytest.approx(538.5, abs=0.1)
    assert hud.marks.crosshair == (991, 696)
    assert hud.marks.aim == hud.solution


def test_stale_with_its_age_once_the_map_is_closed():
    hud = build_hud(MapState(player=FIX, target=TARGET), now=147.9)
    assert hud.fix is Fix.STALE
    assert hud.fix_age_s == 47
    assert hud.solution is not None and hud.marks is None


def test_no_line_is_drawn_while_the_cursor_is_on_the_player():
    on_arrow = MapReading(
        PANEL,
        crosshair=(942, 571),
        cursor=(83.0, 73.0),
        player=(942, 571),
        heading=90,
        player_coords=(83.0, 73.0),
    )
    hud = build_hud(MapState(on_arrow, frame_size=SIZE, player=FIX, target=TARGET), now=100.0)
    assert hud.marks.aim is None and hud.marks.crosshair is None
    assert hud.solution is not None  # the earlier target still stands


def test_the_model_only_changes_when_something_to_draw_does():
    state = MapState(player=FIX, target=TARGET)
    assert build_hud(state, now=147.1) == build_hud(state, now=147.9)
    assert build_hud(state, now=147.9) != build_hud(state, now=148.0)
    # Past a minute the age is shown in minutes, so seconds no longer matter.
    assert build_hud(state, now=225.0) == build_hud(state, now=279.9)
    assert build_hud(state, now=279.9) != build_hud(state, now=280.0)
    assert build_hud(state, now=147.0) != build_hud(replace(state, target=None), now=147.0)


def test_toast_shows_for_a_while():
    toast = Toast(seconds=2.0)
    assert toast.current(now=0.0) is None
    toast.show("Screenshot saved", now=10.0)
    assert toast.current(now=11.9) == "Screenshot saved"
    assert toast.current(now=12.0) is None


def test_formats():
    assert format_range(FiringSolution(558.46, 158.59)) == "558"
    assert format_azimuth(FiringSolution(558.46, 158.59)) == "158.6°"
    assert format_azimuth(FiringSolution(100.0, 359.97)) == "0.0°"
    assert format_heading(90) == "090°"
    assert format_heading(359.7) == "000°"
    assert format_age(47) == "47 s ago"
    assert format_age(125) == "2 min ago"
