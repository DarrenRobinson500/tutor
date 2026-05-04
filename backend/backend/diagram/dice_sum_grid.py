import re
from dataclasses import dataclass
from typing import Optional, Tuple

DIAGRAM_TYPE = "DiceSumGrid"

# Example:
# DiceSumGrid(target: 5, pos: (0,0))

@dataclass
class DiceSumGridDiagram:
    type: str
    target: int
    pos: Tuple[float, float]


DICE_SUM_GRID_REGEX = re.compile(
    r"DiceSumGrid\s*\(\s*target:\s*(?P<target>\d+)\s*,\s*pos:\s*\(\s*(?P<x>-?\d+)\s*,\s*(?P<y>-?\d+)\s*\)\s*\)"
)


def parse(line: str) -> Optional[DiceSumGridDiagram]:
    print("DiceSumGrid parse")
    match = DICE_SUM_GRID_REGEX.match(line)
    if not match:
        print("DiceSumGrid Regex failed")
        return None

    target = int(match.group("target"))
    px = float(match.group("x"))
    py = float(match.group("y"))

    return DiceSumGridDiagram(
        type="DiceSumGrid",
        target=target,
        pos=(px, py)
    )


def render(diagram: DiceSumGridDiagram) -> str:
    target = diagram.target
    px, py = diagram.pos

    cell = 5          # size of each square
    gap = 0            # gap between squares
    header = 5        # space for labels

    grid_size = 6 * (cell + gap) - gap
    total_width = grid_size + header
    total_height = grid_size + header

    # Center the whole diagram at pos
    x0 = px - total_width / 2
    y0 = py - total_height / 2

    fragments = []

    # Column headers (1–6)
    for col in range(1, 7):
        cx = x0 + header + (col - 1) * (cell + gap) + cell / 2
        cy = y0 + header / 2 + 1
        fragments.append(
            f'<text x="{cx}" y="{cy}" text-anchor="middle" font-size="3">{col}</text>'
        )

    # Row headers (1–6)
    for row in range(1, 7):
        cx = x0 + header / 2
        cy = y0 + header + (row - 1) * (cell + gap) + cell / 2 + 1
        fragments.append(
            f'<text x="{cx}" y="{cy}" text-anchor="middle" font-size="3">{row}</text>'
        )

    # Grid cells
    for row in range(1, 7):
        for col in range(1, 7):
            sum_val = row + col

            x = x0 + header + (col - 1) * (cell + gap)
            y = y0 + header + (row - 1) * (cell + gap)

            fill = "#ffeb3b" if sum_val == target else "white"

            fragments.append(
                f'<rect x="{x}" y="{y}" width="{cell}" height="{cell}" '
                f'stroke="#666" stroke-width="0.2" fill="{fill}" />'
            )

            # Sum text
            fragments.append(
                f'<text x="{x + cell/2}" y="{y + cell/2 + 1}" '
                f'text-anchor="middle" font-size="3">{sum_val}</text>'
            )

    return "\n".join(fragments)