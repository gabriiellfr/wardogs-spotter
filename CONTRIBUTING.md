# Contributing

Issues and pull requests are welcome. This is a hobby project, so answers may
take a few days.

## Setting up

You need Windows, [uv](https://docs.astral.sh/uv/) and git.

```powershell
git clone https://github.com/gabriiellfr/wardogs-spotter
cd wardogs-spotter
uv sync
```

## Before a pull request

```powershell
uv run ruff format .
uv run ruff check .
uv run mypy
uv run pytest
```

CI runs the same four on every push. To run the first two on every commit,
install the hooks once with `uvx pre-commit install`.

## Working without the game

Save a few screenshots with `F8` while the HUD runs. Then:

```powershell
uv run wardogs-spotter read               # what the reader gets from each
uv run wardogs-spotter preview --replay   # the HUD over them, in a loop
```

Both take the game's own images from `screenshots/raw/`. The pictures in
`screenshots/` have the HUD drawn on them and are for looking at.

## Reporting a frame that is read wrong

A screenshot is worth more than a description. Save one with `F8` at the
moment it goes wrong and attach the file from `screenshots/raw/` (the game's
own image, not the one with the HUD in `screenshots/`). Say what the labels on screen
read and what the HUD showed.

Screenshots show the names of the players in your squad. Crop or blur them
before you post one if that matters to you or to them.

## Changing the reader

The reader's behavior on real frames is pinned by `tests/test_vision_frames.py`
and the four frames in `tests/fixtures`. If a change makes it read them
differently, check the new reading against the image itself before updating
`expected.json`: the cursor's coordinates are printed in each frame.

A new kind of frame that used to fail and now works is the best test to add.
Cut it down to the map first, as described in `tests/fixtures/README.md`.

## Releasing

1. Set the new version in `src/wardogs_spotter/__init__.py`.
2. Add its section to `CHANGELOG.md`, with the link at the bottom. A test
   fails while the version has no section.
3. Commit, then tag the commit with the version and push the tag:

   ```powershell
   git tag v0.2.0
   git push origin v0.2.0
   ```

The [Release workflow](.github/workflows/release.yml) takes it from there. It
checks that the tag is the version in the code, runs the tests, builds the
executable with PyInstaller, starts it and has it read the test frames, then
publishes a GitHub release with the zip, its SHA-256 and the changelog section
as the description.

To try the build without releasing, run the workflow by hand from the Actions
tab (the zip ends up in the run's artifacts), or build it on your machine:

```powershell
uv sync --group build
uv run pyinstaller packaging/wardogs-spotter.spec --noconfirm
dist\wardogs-spotter\wardogs-spotter.exe --version
```

## Style

- Comments say why, or what a reader can't see in the code. Constants carry
  their unit and their reason next to them.
- `vision` stays free of threads, windows and Qt; `ui.model` stays free of Qt.
  [docs/architecture.md](docs/architecture.md) has the full table.
