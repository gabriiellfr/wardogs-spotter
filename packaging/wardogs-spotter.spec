# PyInstaller build of the Windows executable.
#
#   uv sync --group build
#   uv run pyinstaller packaging/wardogs-spotter.spec --noconfirm
#
# The result is the folder dist/wardogs-spotter/ with wardogs-spotter.exe in
# it. A folder, not a single file: a single-file executable unpacks itself to
# a temporary folder on every start, which is slow with Qt and OpenCV inside,
# and would lose the glyphs the `learn` command adds.

import os
from pathlib import Path

from PyInstaller.utils.hooks import collect_data_files

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")  # drawing the icon needs no screen

from PySide6.QtGui import QGuiApplication  # noqa: E402

from wardogs_spotter.ui.tray import draw_icon  # noqa: E402

ROOT = Path(SPECPATH).parent
NAME = "wardogs-spotter"

# The executable's icon is the tray icon, drawn larger.
qt = QGuiApplication.instance() or QGuiApplication([])
icon = Path(workpath) / f"{NAME}.ico"
icon.parent.mkdir(parents=True, exist_ok=True)
if not draw_icon(256).save(str(icon)):
    raise SystemExit(f"could not write {icon}")

analysis = Analysis(
    [str(ROOT / "src" / "wardogs_spotter" / "__main__.py")],
    datas=collect_data_files("wardogs_spotter"),  # the glyphs
    excludes=["tkinter"],
)
# Libraries OpenCV and Qt bring along that this program never loads: video
# file codecs, and a software OpenGL for machines without a graphics driver.
UNUSED = ("opencv_videoio_ffmpeg", "opengl32sw")
analysis.binaries = [
    entry for entry in analysis.binaries if not Path(entry[0]).name.startswith(UNUSED)
]
executable = EXE(
    PYZ(analysis.pure),
    analysis.scripts,
    exclude_binaries=True,
    name=NAME,
    icon=str(icon),
    console=True,  # it logs to the terminal, and `read` and `learn` print there
    upx=False,  # packed executables are what antivirus programs distrust most
)
COLLECT(executable, analysis.binaries, analysis.datas, name=NAME, upx=False)
