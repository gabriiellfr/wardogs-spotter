# Test fixtures

`map_1.png` to `map_4.png` are four consecutive moments of one match at
1920x1080, cut down to the map panel plus a 40 px margin. The cut keeps the
files small and leaves out the parts of the screen that show other players'
names.

They are frames of one session, in order: the tracker follows the map from one
to the next, so tests that check the scale or the player's coordinates must
feed them in sequence.

| File | What it shows |
| --- | --- |
| `map_1.png` | Cursor on the map, coordinates readable. The first reading: no scale yet. |
| `map_2.png` | The map panned. The y label is misread (a speck next to it reads as a dot), so this frame gives no cursor reading. |
| `map_3.png` | Cursor moved again. With the reading from `map_1` carried across, the scale is known. |
| `map_4.png` | 90 seconds later: the map zoomed out and the player turned east. The scale follows the zoom. |

`expected.json` holds what the reader gets from each one. The cursor
coordinates can be checked by eye: they are printed in the image.
