"""The reader on real frames (see fixtures/README.md)."""

import cv2
import pytest

from wardogs_spotter.vision import GlyphReader, MapTracker, describe, draw, read_map


@pytest.fixture(scope="module")
def glyphs() -> GlyphReader:
    return GlyphReader()


@pytest.fixture(scope="module")
def readings(frames, glyphs):
    """The frames read in order by one tracker, as in a live session."""
    tracker = MapTracker(glyphs)
    return [tracker.update(frame) for frame in frames]


def test_knows_every_character_of_a_coordinate_label(glyphs):
    assert set(glyphs.chars) == set("xy0123456789")


def test_finds_the_panel_and_the_crosshair(frames, glyphs, expected):
    for frame, want in zip(frames, expected["frames"], strict=True):
        reading = read_map(frame, glyphs)
        assert reading.panel == tuple(expected["panel"])
        assert reading.crosshair == tuple(want["crosshair"])


def test_reads_the_coordinates_at_the_cursor(frames, glyphs, expected):
    for frame, want in zip(frames, expected["frames"], strict=True):
        cursor = read_map(frame, glyphs).cursor
        assert cursor == (tuple(want["cursor"]) if want["cursor"] else None), want["file"]


def test_finds_the_player_arrow_and_heading(frames, glyphs, expected):
    for frame, want in zip(frames, expected["frames"], strict=True):
        reading = read_map(frame, glyphs)
        assert reading.player == tuple(want["player"]), want["file"]
        assert reading.heading == want["heading"], want["file"]


def test_one_frame_alone_gives_no_scale(frames, glyphs):
    for frame in frames:
        assert MapTracker(glyphs).update(frame).scale is None


def test_following_the_map_gives_the_scale(readings, expected):
    for reading, want in zip(readings, expected["frames"], strict=True):
        if want["scale"] is None:
            assert reading.scale is None, want["file"]
        else:
            assert reading.scale == pytest.approx(want["scale"], rel=0.01), want["file"]


def test_the_scale_gives_the_player_coordinates(readings, expected):
    for reading, want in zip(readings, expected["frames"], strict=True):
        if want["player_coords"] is None:
            assert reading.player_coords is None, want["file"]
        else:
            # 0.05 units is 5 m on the ground.
            assert reading.player_coords == pytest.approx(want["player_coords"], abs=0.05)


def test_the_player_stays_put_while_the_view_changes(readings):
    """Frames 3 and 4 are 90 seconds and one zoom level apart, with the
    player around the same spot: the positions worked out from each agree
    to within 15 m."""
    (x3, y3), (x4, y4) = readings[2].player_coords, readings[3].player_coords
    assert abs(x3 - x4) < 0.15 and abs(y3 - y4) < 0.15


def test_a_frame_without_a_map_resets_the_tracker(frames, glyphs):
    tracker = MapTracker(glyphs)
    for frame in frames[:3]:
        tracker.update(frame)
    no_map = cv2.GaussianBlur(frames[0], (0, 0), 25)  # the borders are gone
    assert tracker.update(no_map) is None
    assert tracker.update(frames[2]).scale is None


def test_describe_sums_up_a_reading(readings):
    assert describe(readings[0]).split() == [
        *("cursor", "x80.88", "y70.63"),
        *("player", "on", "map"),
        *("heading", "282"),
        *("scale", "-"),
    ]
    assert "player x83.42 y73.05" in describe(readings[3])
    assert "scale 24.0 px/unit" in describe(readings[3])


def test_draw_marks_a_copy(frames, readings):
    marked = draw(frames[3], readings[3])
    assert marked.shape == frames[3].shape
    assert marked is not frames[3]
    assert (marked != frames[3]).any()
