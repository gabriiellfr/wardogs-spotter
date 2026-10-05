"""What a release is made from: the version and the changelog."""

import importlib.util
from pathlib import Path

import pytest

from wardogs_spotter import __version__

ROOT = Path(__file__).parent.parent


@pytest.fixture(scope="module")
def release_notes():
    """packaging/release_notes.py, which is a script and not part of the package."""
    spec = importlib.util.spec_from_file_location(
        "release_notes", ROOT / "packaging" / "release_notes.py"
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_the_changelog_has_an_entry_for_this_version(release_notes):
    """Bumping the version without writing the changelog fails here, before
    the release workflow refuses to publish."""
    changelog = (ROOT / "CHANGELOG.md").read_text(encoding="utf-8")
    assert release_notes.notes(__version__, changelog).strip()


CHANGELOG = """\
# Changelog

## [0.2.0] - 2026-11-01

### Fixed

- The second thing.

## [0.1.0] - 2026-10-05

The first public version.

[0.2.0]: https://example.test/v0.2.0
[0.1.0]: https://example.test/v0.1.0
"""


def test_notes_are_one_versions_section(release_notes):
    assert release_notes.notes("0.2.0", CHANGELOG) == "### Fixed\n\n- The second thing.\n"


def test_the_last_section_stops_before_the_links(release_notes):
    assert release_notes.notes("0.1.0", CHANGELOG) == "The first public version.\n"


def test_a_version_without_an_entry_is_an_error(release_notes):
    with pytest.raises(SystemExit, match=r"no entry for 0\.3\.0"):
        release_notes.notes("0.3.0", CHANGELOG)
