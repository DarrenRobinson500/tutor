import re
import math
from dataclasses import dataclass, field
from typing import List, Optional

DIAGRAM_TYPE = "Parallelogram"
SUPPORTS_VIZ_SCALE = True

# Syntax: Parallelogram(b: 8, h: 5, labels: true)
#         Parallelogram(b: 8, h: 5, label_b: "8 cm", label_h: "h=5")
# b: base length, h: perpendicular height
# labels: true       →  show numeric values for b and h (auto-formatted)
# label_b: "..."     →  custom label for the base (overrides labels: true for b)
# label_h: "..."     →  custom label for the height line (overrides labels: true for h)
# pos: (x, y)        →  centre offset
# scale: N            →  scale factor

# The top edge is shifted right by h * SLANT_RATIO, giving a consistent lean.
SLANT_RATIO = 0.5


@dataclass
class ParallelogramDiagram:
    b: float
    h: float
    labels: bool = False
    label_b: str = ""
    label_h: str = ""
    pos: List[float] = field(default_factory=lambda: [0.0, 0.0])
    scale: float = 1.0


def parse(line: str) -> Optional[ParallelogramDiagram]:
    def get_num(key):
        m = re.search(rf'\b{key}:\s*(-?[\d.]+)', line)
        return float(m.group(1)) if m else None

    def get_str(key):
        m = re.search(rf'\b{key}[=:]\s*"([^"]*)"', line)
        if m:
            return m.group(1)
        m = re.search(rf'\b{key}[=:]\s*([^,)\s]+)', line)
        return m.group(1) if m else ""

    b = get_num("b")
    h = get_num("h")
    if b is None or h is None:
        return None

    pos_match = re.search(r'\bpos:\s*\(\s*(-?[\d.]+)\s*,\s*(-?[\d.]+)\s*\)', line)
    pos = [float(pos_match.group(1)), float(pos_match.group(2))] if pos_match else [0.0, 0.0]
    scale = get_num("scale") or 1.0

    labels_match = re.search(r'\blabels:\s*(true|false)', line)
    labels = (labels_match.group(1) != "false") if labels_match else False

    # Individual labels — fall back to auto-formatted value when labels: true
    label_b = get_str("label_b") or (_fmt(b) if labels else "")
    label_h = get_str("label_h") or (_fmt(h) if labels else "")

    return ParallelogramDiagram(
        b=b, h=h, labels=labels,
        label_b=label_b, label_h=label_h,
        pos=pos, scale=scale,
    )


def render(d: ParallelogramDiagram, viz_scale: float = None) -> str:
    b = d.b * d.scale
    h = d.h * d.scale
    cx0, cy0 = d.pos
    offset = h * SLANT_RATIO   # horizontal shift of the top edge

    # Vertices centred at pos (SVG: y increases downward)
    # Math layout: A=(0,0) B=(b,0) C=(b+offset,h) D=(offset,h)
    # Centre of bounding box: ((b+offset)/2, h/2)
    half_w = (b + offset) / 2
    half_h = h / 2

    sAx = cx0 - half_w;              sAy = cy0 + half_h   # bottom-left
    sBx = cx0 - half_w + b;          sBy = cy0 + half_h   # bottom-right
    sCx = cx0 - half_w + b + offset; sCy = cy0 - half_h   # top-right
    sDx = cx0 - half_w + offset;     sDy = cy0 - half_h   # top-left

    if viz_scale is None:
        content_w = b + offset
        content_h = h
        content_span = max(content_w, content_h * (60.0 / 36.0))
        expected_vw = content_span / 0.92
        viz_scale = expected_vw / 60.0

    sw        = 0.192 * viz_scale
    font_size = 2.0   * viz_scale
    ra_size   = 2.0   * viz_scale
    out = []

    # Parallelogram outline
    pts = (f"{sAx:.3f},{sAy:.3f} {sBx:.3f},{sBy:.3f} "
           f"{sCx:.3f},{sCy:.3f} {sDx:.3f},{sDy:.3f}")
    out.append(
        f'<polygon points="{pts}" fill="none" stroke="black" '
        f'stroke-width="{sw}" stroke-linejoin="round" stroke-linecap="round"/>'
    )

    # Equal-side tick marks
    # Bottom (A→B) and top (D→C) are both length b — single tick
    # Left leg (A→D) and right leg (B→C) are equal slanted sides — double tick
    tick_size  = 1.1 * viz_scale
    tick_sw    = 0.14 * viz_scale
    arrow_size = 1.0 * viz_scale
    out.append(_tick_mark(sAx, sAy, sBx, sBy, 1, tick_size, tick_sw))
    out.append(_tick_mark(sDx, sDy, sCx, sCy, 1, tick_size, tick_sw))
    out.append(_tick_mark(sAx, sAy, sDx, sDy, 2, tick_size, tick_sw))
    out.append(_tick_mark(sBx, sBy, sCx, sCy, 2, tick_size, tick_sw))
    # Parallel-side arrows — offset to t=0.35 so they don't overlap the midpoint ticks
    out.append(_parallel_arrow(sAx, sAy, sBx, sBy, 1, arrow_size, tick_sw, t=0.35))
    out.append(_parallel_arrow(sDx, sDy, sCx, sCy, 1, arrow_size, tick_sw, t=0.35))
    out.append(_parallel_arrow(sAx, sAy, sDx, sDy, 2, arrow_size, tick_sw, t=0.35))
    out.append(_parallel_arrow(sBx, sBy, sCx, sCy, 2, arrow_size, tick_sw, t=0.35))

    # Height line: dotted vertical from D (top-left vertex) to foot on base
    s_foot_x = sDx
    s_foot_y = sAy   # base y

    dash = f"{sw * 3:.2f},{sw * 2:.2f}"
    out.append(
        f'<line x1="{sDx:.3f}" y1="{sDy:.3f}" x2="{s_foot_x:.3f}" y2="{s_foot_y:.3f}" '
        f'stroke="black" stroke-width="{sw}" stroke-dasharray="{dash}" stroke-linecap="round"/>'
    )

    # Right-angle marker at foot (up toward D, right along base)
    out.append(_right_angle_marker(s_foot_x, s_foot_y, math.pi / 2, 0.0, ra_size, sw))

    # Labels are suppressed in pass 1 (viz_scale == 1.0) so they don't inflate
    # the bbox used to compute global_viz_scale. They are rendered in pass 2.
    if viz_scale != 1.0:
        # Base label: centred below bottom edge
        if d.label_b:
            out.append(_text((sAx + sBx) / 2, sAy + font_size * 1.4, d.label_b, font_size))

        # Height label: 30% from base to top, offset to the right of the dotted line.
        # Clamped upward so it always clears the right-angle marker at the base.
        if d.label_h:
            lx = s_foot_x + font_size * 1.2
            ly = s_foot_y + 0.3 * (sDy - s_foot_y)
            ly = min(ly, s_foot_y - ra_size * 3 - font_size * 0.5)
            out.append(_text(lx, ly, d.label_h, font_size))

    return "\n".join(p for p in out if p)


# ── Helpers ───────────────────────────────────────────────────────────────────

def _parallel_arrow(x1, y1, x2, y2, count: int, arrow_size: float, sw: float, t: float = 0.5) -> str:
    """Draw `count` chevron arrow(s) at position t along a segment, pointing along it."""
    mx, my = x1 + t * (x2 - x1), y1 + t * (y2 - y1)
    dx, dy = x2 - x1, y2 - y1
    length = math.hypot(dx, dy)
    if length == 0:
        return ""
    ux, uy = dx / length, dy / length
    px, py = -uy, ux

    spacing = arrow_size * 0.8
    start_offset = -(count - 1) * spacing / 2
    frags = []
    for i in range(count):
        along = start_offset + i * spacing
        cx = mx + along * ux
        cy = my + along * uy
        tip_x  = cx + ux * arrow_size * 0.6
        tip_y  = cy + uy * arrow_size * 0.6
        base_x = cx - ux * arrow_size * 0.6
        base_y = cy - uy * arrow_size * 0.6
        frags.append(
            f'<polyline points="{base_x + px * arrow_size:.3f},{base_y + py * arrow_size:.3f} '
            f'{tip_x:.3f},{tip_y:.3f} '
            f'{base_x - px * arrow_size:.3f},{base_y - py * arrow_size:.3f}" '
            f'fill="none" stroke="black" stroke-width="{sw:.3f}" '
            f'stroke-linejoin="round" stroke-linecap="round"/>'
        )
    return "\n".join(frags)


def _tick_mark(x1, y1, x2, y2, count: int, tick_size: float, sw: float) -> str:
    """Draw `count` tick marks perpendicular to a line segment, centred on its midpoint."""
    mx, my = (x1 + x2) / 2, (y1 + y2) / 2
    dx, dy = x2 - x1, y2 - y1
    length = math.hypot(dx, dy)
    if length == 0:
        return ""
    ux, uy = dx / length, dy / length
    px, py = -uy, ux

    spacing = tick_size * 0.65
    start_offset = -(count - 1) * spacing / 2
    frags = []
    for i in range(count):
        along = start_offset + i * spacing
        cx = mx + along * ux
        cy = my + along * uy
        frags.append(
            f'<line x1="{cx - px * tick_size:.3f}" y1="{cy - py * tick_size:.3f}" '
            f'x2="{cx + px * tick_size:.3f}" y2="{cy + py * tick_size:.3f}" '
            f'stroke="black" stroke-width="{sw:.3f}" stroke-linecap="round"/>'
        )
    return "\n".join(frags)


def _right_angle_marker(vx, vy, ang_to_a, ang_to_b, size, sw):
    """Small square at a point to indicate a 90° angle."""
    ux_a = math.cos(ang_to_a); uy_a = -math.sin(ang_to_a)   # SVG y-inverted
    ux_b = math.cos(ang_to_b); uy_b = -math.sin(ang_to_b)
    p1x = vx + size * ux_a;  p1y = vy + size * uy_a
    p2x = vx + size * ux_b;  p2y = vy + size * uy_b
    p3x = p1x + size * ux_b; p3y = p1y + size * uy_b
    return (
        f'<path d="M{p1x:.3f},{p1y:.3f} L{p3x:.3f},{p3y:.3f} L{p2x:.3f},{p2y:.3f}" '
        f'fill="none" stroke="black" stroke-width="{sw:.3f}" '
        f'stroke-linejoin="miter" stroke-linecap="butt"/>'
    )


def _text(x, y, text, font_size):
    return (
        f'<text x="{x:.3f}" y="{y:.3f}" font-size="{font_size}" '
        f'font-family="system-ui, -apple-system, sans-serif" '
        f'text-anchor="middle" dominant-baseline="middle">{text}</text>'
    )


def _fmt(n: float) -> str:
    return str(int(n)) if n == int(n) else f"{n:g}"
