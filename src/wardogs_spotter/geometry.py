"""The coordinate types the rest of the package talks in.

Two spaces are in play. Pixels locate things in a captured frame, with y
growing downward. Game coordinates are the map's own: x grows to the east, y
to the north, as the game prints them next to the cursor.
"""

Pixel = tuple[int, int]  # (px, py) in a frame
Coords = tuple[float, float]  # (x, y) in game coordinates
Rect = tuple[int, int, int, int]  # (left, top, right, bottom) in a frame
Box = tuple[int, int, int, int]  # (x, y, w, h) in a frame
Size = tuple[int, int]  # (w, h)


def format_coords(coords: Coords) -> str:
    """Game coordinates the way the game prints them: "x99.23 y109.58"."""
    return f"x{coords[0]:.2f} y{coords[1]:.2f}"
