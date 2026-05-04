import re
import math
from dataclasses import dataclass
from typing import Tuple, Optional

DIAGRAM_TYPE = "Balls"

# Syntax: Balls(red: 3, blue: 5, green: 2, yellow: 1, white: 2, pos: (0, 0), scale: 1)
#
# Each colour parameter is the count of balls of that colour.
# All colours are optional (default 0); at least one must be non-zero.
#
# Example: Balls(red: 7, blue: 2)  → 7 red + 2 blue = 9 total


@dataclass
class BallsDiagram:
    red: int = 0
    blue: int = 0
    green: int = 0
    yellow: int = 0
    white: int = 0
    pos: Tuple[float, float] = (0.0, 0.0)
    scale: float = 1.0


def parse(line: str) -> Optional[BallsDiagram]:
    def get_int(key):
        m = re.search(rf'\b{key}:\s*(\d+)', line)
        return int(m.group(1)) if m else 0

    pos_match = re.search(r'\bpos:\s*\(\s*(-?[\d.]+)\s*,\s*(-?[\d.]+)\s*\)', line)

    red    = get_int("red")
    blue   = get_int("blue")
    green  = get_int("green")
    yellow = get_int("yellow")
    white  = get_int("white")

    if red + blue + green + yellow + white == 0:
        return None

    pos = (float(pos_match.group(1)), float(pos_match.group(2))) if pos_match else (0.0, 0.0)

    def get_scale():
        m = re.search(r'\bscale:\s*([\d.]+)', line)
        return float(m.group(1)) if m else 1.0

    return BallsDiagram(red=red, blue=blue, green=green, yellow=yellow, white=white,
                        pos=pos, scale=get_scale())


_COLOURS = {
    "red":    ("#e63946", "#9b2226"),
    "blue":   ("#4895ef", "#1d3557"),
    "green":  ("#2dc653", "#1a7431"),
    "yellow": ("#ffd166", "#b8860b"),
    "white":  ("#ffffff", "#888888"),
}


def render(d: BallsDiagram) -> str:
    cx0, cy0 = d.pos
    scale = d.scale

    balls = (
        ["red"]    * d.red  +
        ["blue"]   * d.blue +
        ["green"]  * d.green +
        ["yellow"] * d.yellow +
        ["white"]  * d.white
    )
    total = len(balls)
    if total == 0:
        return ""

    r = 1.4 * scale
    spacing = r * 2 + 0.5 * scale

    ncols = min(total, 5) if total <= 10 else min(total, 8)
    nrows = math.ceil(total / ncols)

    sw = 0.2 * scale
    out = []

    for i, color in enumerate(balls):
        row = i // ncols
        col = i % ncols

        # Centre the last (possibly short) row
        row_count = total - row * ncols if row == nrows - 1 else ncols
        col_offset = (ncols - row_count) / 2.0

        bx = cx0 + (col + col_offset - (ncols - 1) / 2.0) * spacing
        by = cy0 + (row - (nrows - 1) / 2.0) * spacing

        fill, stroke = _COLOURS[color]
        out.append(
            f'<circle cx="{bx:.3f}" cy="{by:.3f}" r="{r:.3f}" '
            f'fill="{fill}" stroke="{stroke}" stroke-width="{sw:.3f}"/>'
        )

    return "\n".join(out)
