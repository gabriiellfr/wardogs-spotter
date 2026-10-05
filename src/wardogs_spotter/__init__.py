"""Wardogs Spotter: reads the in-game map off the screen and shows the range
and azimuth from you to your target in a HUD drawn over the game."""

import os

# numpy's math library reserves a working buffer per CPU thread at import,
# hundreds of MB that this program never uses; one thread is plenty. It is set
# here because the package is imported before any module that imports numpy.
os.environ.setdefault("OPENBLAS_NUM_THREADS", "1")

__version__ = "0.1.0"
