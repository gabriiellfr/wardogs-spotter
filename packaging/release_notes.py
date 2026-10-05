"""Write one version's section of CHANGELOG.md to a file, for the release page.

usage: python packaging/release_notes.py VERSION OUTPUT

Fails when the changelog has no entry for the version, so a release can't go
out without one.
"""

import re
import sys
from pathlib import Path

CHANGELOG = Path(__file__).resolve().parent.parent / "CHANGELOG.md"


def notes(version: str, changelog: str) -> str:
    """The text under the `## [version]` heading, up to the next version's
    heading or the link definitions at the end."""
    section = re.search(
        rf"^## \[{re.escape(version)}\][^\n]*\n(.*?)(?=^## \[|^\[[^\]\n]+\]: |\Z)",
        changelog,
        re.MULTILINE | re.DOTALL,
    )
    if not section or not section.group(1).strip():
        raise SystemExit(f"CHANGELOG.md has no entry for {version}")
    return section.group(1).strip() + "\n"


if __name__ == "__main__":
    version, output = sys.argv[1:]
    text = notes(version, CHANGELOG.read_text(encoding="utf-8"))
    Path(output).parent.mkdir(parents=True, exist_ok=True)
    Path(output).write_text(text, encoding="utf-8", newline="\n")
    print(f"Release notes for {version}: {len(text.splitlines())} lines in {output}")
