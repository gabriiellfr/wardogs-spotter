"""Frames as Qt images, with or without the HUD on them."""

import numpy as np
from PySide6.QtCore import QRectF
from PySide6.QtGui import QImage, QPainter

from wardogs_spotter.ui.hud import HudPainter
from wardogs_spotter.ui.model import HudModel


def to_qimage(frame: np.ndarray) -> QImage:
    """The BGR frame as a QImage that shares its pixels (no copy): the frame
    must stay alive, and unchanged, for as long as the image is used."""
    height, width = frame.shape[:2]
    return QImage(frame.data, width, height, frame.strides[0], QImage.Format.Format_BGR888)


def compose(frame: np.ndarray, hud: HudPainter, model: HudModel, scale: float = 1.0) -> QImage:
    """A copy of the frame with the HUD painted on it: the game as it looked
    on screen. (The capture itself never contains the overlay.)"""
    image = to_qimage(frame).convertToFormat(QImage.Format.Format_ARGB32_Premultiplied)
    painter = QPainter(image)
    hud.paint(painter, QRectF(image.rect()), model, scale)
    painter.end()
    return image
