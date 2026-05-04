import re
from dataclasses import dataclass
from typing import Optional, Tuple, List

DIAGRAM_TYPE = "GraphPie"

@dataclass
class GraphPieDiagram:
    type: str
    points: List[Tuple[str, float]]  # [(label, value), ...]
    pos: Tuple[float, float]         # (px, py) chart center

# Example:
# GraphPie(points: [("Pizza", 15), ("Pasta", 18)], pos: (0,0))

GRAPH_PIE_REGEX = re.compile(
    r'GraphPie\s*\(\s*'
    r'points:\s*\[(?P<pts>.+?)\]\s*,\s*'
    r'pos:\s*\(\s*(?P<x>-?\d+(?:\.\d*)?)\s*,\s*(?P<y>-?\d+(?:\.\d*)?)\s*\)\s*'
    r'\)\s*$'
)

# Accept pairs like ("Label", 12.3); allow straight or curly quotes
PAIR_REGEX = re.compile(
    r'\(\s*([\"“”])(.*?)\1\s*,\s*(-?\d+(?:\.\d*)?)\s*\)'
)

def parse(line: str) -> Optional[GraphPieDiagram]:
    print("Pie Parse")
    m = GRAPH_PIE_REGEX.match(line)
    if not m:
        return None

    pts_raw = m.group("pts")
    px = float(m.group("x"))
    py = float(m.group("y"))

    points: List[Tuple[str, float]] = []
    for _, label, value in PAIR_REGEX.findall(pts_raw):
        points.append((label, float(value)))

    if not points:
        return None

    return GraphPieDiagram(
        type=DIAGRAM_TYPE,
        points=points,
        pos=(px, py),
    )

def _polar_to_cartesian(cx: float, cy: float, r: float, angle_deg: float) -> Tuple[float, float]:
    import math
    rad = math.radians(angle_deg)
    return cx + r * math.cos(rad), cy + r * math.sin(rad)

def render(diagram: GraphPieDiagram) -> str:
    """
    Returns ONLY SVG fragments so the engine can wrap them.
    The layout fits the engine's viewBox (-25..25 x -15..15).
    """
    pts = diagram.points
    px, py = diagram.pos

    # --- Layout constants (engine user units) ---
    radius = 11.0          # fits comfortably inside -25..25, -15..15
    label_radius = 13.5    # for labels just outside the pie
    stroke_color = "#ffffff"
    stroke_width = 0.3

    total = sum(v for _, v in pts) or 1.0

    # Simple color palette; cycles if more slices than colors
    palette = [
        "#4e79a7", "#f28e2b", "#e15759", "#76b7b2",
        "#59a14f", "#edc948", "#b07aa1", "#ff9da7",
        "#9c755f", "#bab0ab",
    ]

    frags: List[str] = []

    import math
    start_angle = -90.0  # start at top

    for i, (label, value) in enumerate(pts):
        # Skip zero or negative values visually
        if value <= 0:
            continue

        slice_angle = 360.0 * (value / total)
        end_angle = start_angle + slice_angle

        # Points on the arc
        x_start, y_start = _polar_to_cartesian(px, py, radius, start_angle)
        x_end, y_end = _polar_to_cartesian(px, py, radius, end_angle)

        # Large-arc flag
        large_arc = 1 if slice_angle > 180.0 else 0

        color = palette[i % len(palette)]

        # Slice path (move to center, line to start, arc to end, close)
        d = (
            f"M {px},{py} "
            f"L {x_start},{y_start} "
            f"A {radius},{radius} 0 {large_arc},1 {x_end},{y_end} Z"
        )

        frags.append(
            f'<path d="{d}" fill="{color}" stroke="{stroke_color}" stroke-width="{stroke_width}" />'
        )

        # Label at mid-angle
        mid_angle = start_angle + slice_angle / 2.0
        lx, ly = _polar_to_cartesian(px, py, label_radius, mid_angle)

        frags.append(
            f'<text x="{lx}" y="{ly}" font-size="2.2" text-anchor="middle" '
            f'fill="#333">{label}</text>'
        )

        start_angle = end_angle

    return "\n".join(frags)