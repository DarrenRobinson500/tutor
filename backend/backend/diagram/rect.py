import re
import math
from dataclasses import dataclass, field
from typing import Optional, Tuple

DIAGRAM_TYPE = "Rect"
SUPPORTS_VIZ_SCALE = True

# Syntax: Rect(x: 5, y: 3, pos: (0, 0), scale: 1, labels: true)
# labels: true (default) shows dimension labels; labels: false hides them


@dataclass
class RectDiagram:
    x: float
    y: float
    pos: Tuple[float, float] = (0.0, 0.0)
    scale: float = 1.0
    labels: bool = True
    name: str = ""
    right_angle: bool = False


def parse(line: str) -> Optional[RectDiagram]:
    def get_num(key):
        m = re.search(rf'\b{key}:\s*(-?[\d.]+)', line)
        return float(m.group(1)) if m else None

    pos_match = re.search(r'\bpos:\s*\(\s*(-?[\d.]+)\s*,\s*(-?[\d.]+)\s*\)', line)
    labels_match = re.search(r'\blabels:\s*(true|false)', line)
    name_match = re.search(r'\bname:\s*["\']([^"\']*)["\']', line)

    x = get_num("x") or get_num("width")
    y = get_num("y") or get_num("height")

    if x is None or y is None:
        return None

    pos = (float(pos_match.group(1)), float(pos_match.group(2))) if pos_match else (0.0, 0.0)
    scale = get_num("scale") or 1.0
    labels = (labels_match.group(1) != "false") if labels_match else True
    name = name_match.group(1) if name_match else ""

    ra_match = re.search(r'\bright_angle:\s*(true|false)', line)
    right_angle = (ra_match.group(1) == "true") if ra_match else False

    result = RectDiagram(x=x, y=y, pos=pos, scale=scale, labels=labels, name=name, right_angle=right_angle)
    print(f"Rect parse: x={x}, y={y}, pos={pos}, scale={scale}, labels={labels}, name={name!r}")
    return result


def render(d: RectDiagram, viz_scale: float = None) -> str:
    if viz_scale is None:
        viz_scale = 1.0

    cx, cy = d.pos
    w = d.x * d.scale
    h = d.y * d.scale

    # SVG: y increases downward, so top-left corner:
    x0 = cx - w / 2
    y0 = cy - h / 2

    sw = 0.16 * viz_scale
    font_size = 2.0 * viz_scale
    out = []

    out.append(
        f'<rect x="{x0:.3f}" y="{y0:.3f}" width="{w:.3f}" height="{h:.3f}" '
        f'fill="none" stroke="black" stroke-width="{sw}"/>'
    )

    if d.right_angle:
        ra = 1.6 * viz_scale   # square marker size
        ra_sw = sw * 0.85
        # corners: (x, y, dir_along_width, dir_along_height) in SVG coords
        corners = [
            (x0,     y0 + h,  1,  -1),   # bottom-left:  right & up
            (x0 + w, y0 + h, -1,  -1),   # bottom-right: left  & up
            (x0 + w, y0,     -1,   1),   # top-right:    left  & down
            (x0,     y0,      1,   1),   # top-left:     right & down
        ]
        for (vx, vy, sx, sy) in corners:
            p1x, p1y = vx + sx * ra, vy
            p2x, p2y = vx + sx * ra, vy + sy * ra
            p3x, p3y = vx,           vy + sy * ra
            out.append(
                f'<path d="M{p1x:.3f},{p1y:.3f} L{p2x:.3f},{p2y:.3f} L{p3x:.3f},{p3y:.3f}" '
                f'fill="none" stroke="black" stroke-width="{ra_sw:.3f}" '
                f'stroke-linejoin="miter" stroke-linecap="butt"/>'
            )

    if d.name:
        out.append(
            f'<text x="{cx:.3f}" y="{cy + font_size * 0.35:.3f}" text-anchor="middle" '
            f'font-size="{font_size}" font-family="system-ui, -apple-system, sans-serif" fill="#333">{d.name}</text>'
        )

    if d.labels:
        # Width label: centred below the bottom edge
        lx = cx
        ly = y0 + h + font_size * 1.4
        out.append(
            f'<text x="{lx:.3f}" y="{ly:.3f}" text-anchor="middle" '
            f'font-size="{font_size}" font-family="system-ui, -apple-system, sans-serif" fill="#333">{_fmt(d.x)}</text>'
        )

        # Height label: centred to the left of the left edge, no rotation
        hx = x0 - font_size * 0.9
        hy = cy + font_size * 0.35
        out.append(
            f'<text x="{hx:.3f}" y="{hy:.3f}" text-anchor="middle" '
            f'font-size="{font_size}" font-family="system-ui, -apple-system, sans-serif" fill="#333">{_fmt(d.y)}</text>'
        )

    return "\n".join(out)


def _fmt(n: float) -> str:
    """Format a number: strip unnecessary trailing zeros."""
    return str(int(n)) if n == int(n) else f"{n:g}"
