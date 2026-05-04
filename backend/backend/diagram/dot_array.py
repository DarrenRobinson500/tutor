import re
from dataclasses import dataclass
from typing import Optional, Tuple

DIAGRAM_TYPE = "DotArray"

# DotArray(count: 2x2, pos: (0, 0))

@dataclass
class DotArrayDiagram:
    type: str
    rows: int
    cols: int
    pos: Tuple[float, float]


DOTARRAY_REGEX = re.compile(
    r"DotArray\s*\(\s*count:\s*(?P<count>\d+(?:x\d+)?)\s*,\s*pos:\s*\(\s*(?P<x>-?\d+)\s*,\s*(?P<y>-?\d+)\s*\)\s*\)"
)

def parse(line: str) -> Optional[DotArrayDiagram]:
    print("DotArray parse")
    match = DOTARRAY_REGEX.match(line)
    if not match:
        print("DotArray Regex failed")
        return None

    count_str = match.group("count")
    px = float(match.group("x"))
    py = float(match.group("y"))

    # Support "3" or "3x4"
    if "x" in count_str:
        rows, cols = map(int, count_str.split("x"))
    else:
        rows = 1
        cols = int(count_str)

    return DotArrayDiagram(type="DotArray", rows=rows, cols=cols, pos=(px, py))


def render(dotarray: DotArrayDiagram) -> str:
    rows = dotarray.rows
    cols = dotarray.cols
    px, py = dotarray.pos

    radius = 1.5
    spacing = 4

    # Compute total width/height
    width = (cols - 1) * spacing
    height = (rows - 1) * spacing

    # Top-left corner so that the *center* is at pos
    x0 = px - width / 2
    y0 = py - height / 2

    fragments = []
    for r in range(rows):
        for c in range(cols):
            cx = x0 + c * spacing
            cy = y0 + r * spacing
            fragments.append(
                f'<circle cx="{cx}" cy="{cy}" r="{radius}" fill="black" />'
            )

    return "\n".join(fragments)
