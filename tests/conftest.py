import json
from pathlib import Path

import cv2
import numpy as np
import pytest

FIXTURES = Path(__file__).parent / "fixtures"


@pytest.fixture(scope="session")
def expected() -> dict:
    """What the reader gets from the fixture frames."""
    return json.loads((FIXTURES / "expected.json").read_text())


@pytest.fixture(scope="session")
def frames(expected: dict) -> list[np.ndarray]:
    """The fixture frames, in the order they were captured. Don't modify them."""
    return [cv2.imread(str(FIXTURES / frame["file"])) for frame in expected["frames"]]


@pytest.fixture(scope="session")
def qapp():
    """Qt needs an application before it can measure or draw text."""
    from PySide6.QtGui import QGuiApplication

    return QGuiApplication.instance() or QGuiApplication([])
