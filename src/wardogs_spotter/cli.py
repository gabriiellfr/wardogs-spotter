"""The command line: what to run, and with which settings."""

import argparse
import logging
import sys
from dataclasses import replace
from pathlib import Path

from wardogs_spotter import __version__
from wardogs_spotter.config import GameWindow, Settings

COMMANDS = ("run", "preview", "read", "learn")
DEFAULTS = Settings()


def _live_options() -> argparse.ArgumentParser:
    """Options shared by the commands that run on live or replayed frames."""
    options = argparse.ArgumentParser(add_help=False)
    options.add_argument(
        "--hud-scale",
        type=float,
        default=DEFAULTS.hud_scale,
        metavar="FACTOR",
        help="size of the HUD bar and its text (default: %(default)s)",
    )
    options.add_argument(
        "--screenshots",
        type=Path,
        default=DEFAULTS.screenshots_dir,
        metavar="DIR",
        help="where F8 saves screenshots (default: %(default)s)",
    )
    options.add_argument(
        "--seconds",
        type=float,
        default=0.0,
        metavar="N",
        help="stop after this many seconds (default: run until quit)",
    )
    options.add_argument(
        "--title",
        default=DEFAULTS.game.title,
        help="title of the game window (default: %(default)s)",
    )
    options.add_argument(
        "--window-class",
        default=DEFAULTS.game.window_class,
        metavar="CLASS",
        help="class of the game window (default: %(default)s)",
    )
    return options


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="wardogs-spotter",
        description="Reads the Wardogs in-game map off the screen and shows the range and "
        "azimuth from you to your target. Without a command, runs the HUD over the game.",
    )
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    parser.add_argument("-v", "--verbose", action="store_true", help="log more")
    commands = parser.add_subparsers(dest="command", metavar="COMMAND")
    live = _live_options()

    commands.add_parser(
        "run",
        parents=[live],
        help="draw the HUD over the game (the default)",
        description="Draw the HUD over the game window, in a transparent, click-through "
        "window. The game must run borderless or windowed.",
    )

    preview = commands.add_parser(
        "preview",
        parents=[live],
        help="show the capture in a window, with the HUD and the reader's numbers",
        description="Show the captured frames in a window with the HUD over them and what "
        "the reader is doing. S saves a screenshot; Q or Esc quits.",
    )
    preview.add_argument(
        "--replay",
        type=Path,
        nargs="*",
        metavar="PATH",
        help="play saved screenshots in a loop instead of capturing the game: these files or "
        f"folders, or the ones F8 saved in {DEFAULTS.raw_screenshots_dir}/ when none is named",
    )

    read = commands.add_parser(
        "read",
        help="read saved screenshots and save copies with the reading marked",
        description="Read screenshots in order, as the frames of one session, print what "
        "each one gave, and save copies with the reading marked in a read/ folder next to them.",
    )
    read.add_argument(
        "images",
        type=Path,
        nargs="*",
        help=f"screenshots or folders of them (default: {DEFAULTS.raw_screenshots_dir}/)",
    )

    learn = commands.add_parser(
        "learn",
        help="teach the reader the glyphs of a screenshot",
        description="Cut the glyphs of the coordinate labels in each screenshot and add "
        "them to the ones the reader knows.",
    )
    learn.add_argument("images", type=Path, nargs="+", help="screenshots with the map open")
    learn.add_argument(
        "--labels",
        required=True,
        help='the labels on screen, top to bottom, e.g. "y109.58 x99.23"',
    )
    return parser


def _settings(args: argparse.Namespace) -> Settings:
    return replace(
        DEFAULTS,
        game=GameWindow(args.title, args.window_class),
        screenshots_dir=args.screenshots,
        hud_scale=args.hud_scale,
    )


def expand(paths: list[Path]) -> list[Path]:
    """The paths, with each folder replaced by the .png files in it, by name."""
    files: list[Path] = []
    for path in paths:
        files += sorted(path.glob("*.png")) if path.is_dir() else [path]
    return files


def _screenshots(named: list[Path], default: Path) -> list[Path]:
    """The screenshots named on the command line, or the ones in the default
    folder when none was named. The game's own images, not the ones with the
    HUD on them: its marks would be read as part of the map."""
    if named:
        return expand(named)
    return expand([default]) if default.is_dir() else []


def main(argv: list[str] | None = None) -> int:
    argv = sys.argv[1:] if argv is None else list(argv)
    parser = build_parser()
    # No command means "run": `wardogs-spotter --hud-scale 1.2` works too.
    if not any(arg in COMMANDS or arg in ("-h", "--help", "--version") for arg in argv):
        flags = [arg for arg in argv if arg in ("-v", "--verbose")]
        argv = [*flags, "run", *(arg for arg in argv if arg not in flags)]
    args = parser.parse_args(argv)
    logging.basicConfig(level=logging.DEBUG if args.verbose else logging.INFO, format="%(message)s")

    # Each command imports what it needs: reading screenshots needs neither
    # Qt nor a capture, and should start without loading them.
    if args.command == "read":
        from wardogs_spotter.offline import read_screenshots

        paths = _screenshots(args.images, DEFAULTS.raw_screenshots_dir)
        if not paths:
            parser.error("no screenshots: name some, or save them with F8 while the HUD runs")
        read_screenshots(paths)
        return 0

    if args.command == "learn":
        from wardogs_spotter.offline import learn_glyphs

        learn_glyphs(expand(args.images), args.labels.split())
        return 0

    from wardogs_spotter.app import run

    settings = _settings(args)
    replay = None
    if getattr(args, "replay", None) is not None:
        replay = _screenshots(args.replay, settings.raw_screenshots_dir)
        if not replay:
            parser.error("--replay: no screenshots found")
    return run(settings, preview=args.command == "preview", replay=replay, seconds=args.seconds)


if __name__ == "__main__":
    sys.exit(main())
