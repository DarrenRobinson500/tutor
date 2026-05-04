import re
import math
from dataclasses import dataclass, field
from typing import List, Optional

DIAGRAM_TYPE = "Trapezium"
SUPPORTS_VIZ_SCALE = True

# Syntax: Trapezium(a: 5, b: 8, h: 4, labels: true)
#         Trapezium(a: 5, b: 8, h: 4, label_a: "{{ a }} cm", label_b: "{{ b }} cm", label_h: "h")
# a: top edge length, b: base length, h: perpendicular height
# The trapezium is drawn symmetrically (isosceles): top edge centred above the base.
# labels: true       →  show numeric values for a, b, and h (auto-formatted)
# label_a: "..."     →  custom label for the top edge
# label_b: "..."     →  custom label for the base
# label_h: "..."     →  custom label for the height line
# pos: (x, y)        →  centre offset
# scale: N            →  scale factor


@dataclass
class TrapeziumDiagram:
    a: float          # top edge
    b: float          # base
    h: float          # perpendicular height
    labels: bool = False
    label_a: str = ""
    label_b: str = ""
    label_h: str = ""
    pos: List[float] = field(default_factory=lambda: [0.0, 0.0])
    scale: float = 1.0


def parse(line: str) -> Optional[TrapeziumDiagram]:
    def get_num(key):
        m = re.search(rf'\b{key}:\s*(-?[\d.]+)', line)
        return float(m.group(1)) if m else None

    def get_str(key):
        m = re.search(rf'\b{key}[=:]\s*"([^"]*)"', line)
        if m:
            return m.group(1)
        m = re.search(rf'\b{key}[=:]\s*([^,)\s]+)', line)
        return m.group(1) if m else ""

    a = get_num("a")
    b = get_num("b")
    h = get_num("h")
    if a is None or b is None or h is None:
        return None

    pos_match = re.search(r'\bpos:\s*\(\s*(-?[\d.]+)\s*,\s*(-?[\d.]+)\s*\)', line)
    pos = [float(pos_match.group(1)), float(pos_match.group(2))] if pos_match else [0.0, 0.0]
    scale = get_num("scale") or 1.0

    labels_match = re.search(r'\blabels:\s*(true|false)', line)
    labels = (labels_match.group(1) != "false") if labels_match else False

    # Individual labels — fall back to auto-formatted value when labels: true
    label_a = get_str("label_a") or (_fmt(a) if labels else "")
    label_b = get_str("label_b") or (_fmt(b) if labels else "")
    label_h = get_str("label_h") or (_fmt(h) if labels else "")

    return TrapeziumDiagram(
        a=a, b=b, h=h, labels=labels,
        label_a=label_a, label_b=label_b, label_h=label_h,
        pos=pos, scale=scale,
    )


def render(d: TrapeziumDiagram, viz_scale: float = None) -> str:
    a = d.a * d.scale
    b = d.b * d.scale
    h = d.h * d.scale
    cx0, cy0 = d.pos

    # Symmetric (isosceles) trapezium centred at pos (SVG: y increases downward)
    # Math layout: A=(0,0) B=(b,0) C=((b+a)/2, h) D=((b-a)/2, h)
    # Bounding box width = b, height = h, centred at (b/2, h/2)
    sAx = cx0 - b / 2;       sAy = cy0 + h / 2   # bottom-left
    sBx = cx0 + b / 2;       sBy = cy0 + h / 2   # bottom-right
    sCx = cx0 + a / 2;       sCy = cy0 - h / 2   # top-right
    sDx = cx0 - a / 2;       sDy = cy0 - h / 2   # top-left

    if viz_scale is None:
        content_w = max(a, b)
        content_h = h
        content_span = max(content_w, content_h * (60.0 / 36.0))
        expected_vw = content_span / 0.92
        viz_scale = expected_vw / 60.0

    sw        = 0.192 * viz_scale
    font_size = 2.0   * viz_scale
    ra_size   = 2.0   * viz_scale
    out = []

    # Trapezium outline
    pts = (f"{sAx:.3f},{sAy:.3f} {sBx:.3f},{sBy:.3f} "
           f"{sCx:.3f},{sCy:.3f} {sDx:.3f},{sDy:.3f}")
    out.append(
        f'<polygon points="{pts}" fill="none" stroke="black" '
        f'stroke-width="{sw}" stroke-linejoin="round" stroke-linecap="round"/>'
    )

    # Parallel sides (bottom A→B, top D→C) — single chevron arrow each
    arrow_sw   = 0.14 * viz_scale
    arrow_size = 1.1 * viz_scale
    out.append(_parallel_arrow(sAx, sAy, sBx, sBy, 1, arrow_size, arrow_sw))
    out.append(_parallel_arrow(sDx, sDy, sCx, sCy, 1, arrow_size, arrow_sw))

    # Height line: always drawn inside the trapezium.
    # When b >= a: D (top-left) is above the base interior — drop from D to base.
    # When a > b:  A (bottom-left) is below the top edge interior — rise from A to top edge.
    dash = f"{sw * 3:.2f},{sw * 2:.2f}"
    if b >= a:
        h_line_x = sDx          # x = cx0 - a/2, inside base since b >= a
        h_top_y  = sDy
        h_bot_y  = sAy
        # Right-angle marker at the base foot: up (π/2) and right (0)
        out.append(_right_angle_marker(h_line_x, h_bot_y, math.pi / 2, 0.0, ra_size, sw))
    else:
        h_line_x = sAx          # x = cx0 - b/2, inside top edge since a > b
        h_top_y  = sDy
        h_bot_y  = sAy
        # Right-angle marker at the base (bottom): up (π/2) and right (0)
        out.append(_right_angle_marker(h_line_x, h_bot_y, math.pi / 2, 0.0, ra_size, sw))

    out.append(
        f'<line x1="{h_line_x:.3f}" y1="{h_top_y:.3f}" x2="{h_line_x:.3f}" y2="{h_bot_y:.3f}" '
        f'stroke="black" stroke-width="{sw}" stroke-dasharray="{dash}" stroke-linecap="round"/>'
    )

    # Labels are suppressed in pass 1 (viz_scale == 1.0) so they don't inflate
    # the bbox used to compute global_viz_scale. They are rendered in pass 2.
    if viz_scale != 1.0:
        # Top edge label: centred above the top edge
        if d.label_a:
            out.append(_text(cx0, sDy - font_size * 1.4, d.label_a, font_size))

        # Base label: centred below the bottom edge
        if d.label_b:
            out.append(_text(cx0, sAy + font_size * 1.4, d.label_b, font_size))

        # Height label: 30% from base to top, offset to the right of the dotted line
        if d.label_h:
            lx = h_line_x + font_size * 1.2
            ly = h_bot_y + 0.3 * (h_top_y - h_bot_y)
            out.append(_text(lx, ly, d.label_h, font_size))

    return "\n".join(p for p in out if p)


# ── Helpers ───────────────────────────────────────────────────────────────────

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
