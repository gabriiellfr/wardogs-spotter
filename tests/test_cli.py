import shutil
from pathlib import Path

import pytest

from wardogs_spotter import __version__, cli
from wardogs_spotter.cli import expand
from wardogs_spotter.config import Settings

FIXTURES = Path(__file__).parent / "fixtures"


@pytest.fixture
def runs(monkeypatch):
    """Capture what `run` is started with instead of starting it."""
    calls = []

    def fake_run(settings, **options):
        calls.append((settings, options))
        return 0

    monkeypatch.setattr("wardogs_spotter.app.run", fake_run)
    return calls


def test_no_command_runs_the_hud_with_the_defaults(runs):
    assert cli.main([]) == 0
    settings, options = runs[0]
    assert settings == Settings()
    assert options == {"preview": False, "replay": None, "seconds": 0.0}


def test_options_without_a_command_still_mean_run(runs):
    cli.main(["--hud-scale", "1.25", "--title", "Wardogs Test", "--seconds", "5"])
    settings, options = runs[0]
    assert settings.hud_scale == 1.25
    assert settings.game.title == "Wardogs Test"
    assert settings.game.window_class == Settings().game.window_class
    assert options["seconds"] == 5 and not options["preview"]


def test_preview_can_replay_a_folder(runs):
    cli.main(["preview", "--replay", str(FIXTURES)])
    _, options = runs[0]
    assert options["preview"]
    assert [path.name for path in options["replay"]] == [f"map_{n}.png" for n in (1, 2, 3, 4)]


def test_replaying_an_empty_folder_is_an_error(runs, tmp_path):
    with pytest.raises(SystemExit):
        cli.main(["preview", "--replay", str(tmp_path)])
    assert not runs


def test_replay_without_a_path_plays_what_f8_saved(runs, tmp_path):
    """The game's own images, in raw/: the ones next to it have the HUD
    drawn on them, and would be read with its marks as part of the map."""
    raw = tmp_path / "shots" / "raw"
    raw.mkdir(parents=True)
    (raw / "live_1.png").touch()
    (tmp_path / "shots" / "live_1.png").touch()
    cli.main(["preview", "--replay", "--screenshots", str(tmp_path / "shots")])
    _, options = runs[0]
    assert options["replay"] == [raw / "live_1.png"]


def test_read_without_a_path_reads_what_f8_saved(tmp_path, monkeypatch, capsys):
    raw = tmp_path / "screenshots" / "raw"
    raw.mkdir(parents=True)
    shutil.copy(FIXTURES / "map_1.png", raw)
    monkeypatch.chdir(tmp_path)
    assert cli.main(["read"]) == 0
    assert "map_1.png: cursor x80.88 y70.63" in capsys.readouterr().out
    assert (raw / "read" / "map_1.png").is_file()


def test_version(capsys):
    with pytest.raises(SystemExit):
        cli.main(["--version"])
    assert __version__ in capsys.readouterr().out


def test_expand_lists_folders_by_name_and_keeps_files(tmp_path):
    for name in ("b.png", "a.png", "notes.txt"):
        (tmp_path / name).touch()
    single = tmp_path / "single.png"
    assert expand([tmp_path, single]) == [tmp_path / "a.png", tmp_path / "b.png", single]


def test_read_prints_each_frame_and_saves_marked_copies(tmp_path, capsys):
    for path in FIXTURES.glob("map_*.png"):
        shutil.copy(path, tmp_path)
    assert cli.main(["read", str(tmp_path)]) == 0
    out = capsys.readouterr().out
    assert "map_1.png: cursor x80.88 y70.63" in out
    assert "map_4.png: cursor x85.46 y67.85    player x83.42 y73.05" in out
    assert sorted(p.name for p in (tmp_path / "read").iterdir()) == [
        f"map_{n}.png" for n in (1, 2, 3, 4)
    ]


def test_read_without_screenshots_is_an_error(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)  # no screenshots/ folder here
    with pytest.raises(SystemExit):
        cli.main(["read"])


def test_learn_adds_glyphs_for_the_labels_it_is_told(tmp_path, capsys, monkeypatch):
    from wardogs_spotter.vision import labels

    monkeypatch.setattr(labels.GlyphReader.__init__, "__defaults__", (tmp_path,))
    assert cli.main(["learn", str(FIXTURES / "map_1.png"), "--labels", "y70.63 x80.88"]) == 0
    assert "learned 2 of 2 labels" in capsys.readouterr().out
    learned = sorted(path.name for path in tmp_path.iterdir())
    assert learned == sorted(set("y7063x8"))  # one folder per character, none for the dot
