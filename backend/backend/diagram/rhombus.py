import re
import math
from dataclasses import dataclass, field
from typing import List, Optional

DIAGRAM_TYPE = "Rhombus"
SUPPORTS_VIZ_SCALE = True

# Syntax: Rhombus(p: 8, q: 5, label_p: "8", label_q: "5")
# p: horizontal diagonal length, q: vertical diagonal length
# The four vertices are at the midpoints of the bounding box edges.
# labels: true       →  auto-formatted numeric labels for p and q
# label_p: "..."     →  custom label along the horizontal diagonal
# label_q: "..."     →  custom label along the vertical diagonal
# pos: (x, y)        →  centre offset
# scale: N            →  scale factor
#
# Diagonals are drawn as dotted lines with right-angle markers at the centre.


@dataclass
class RhombusDiagram:
    p: float          # horizontal diagonal
    q: float          # vertical diagonal
    labels: bool = False
    label_p: str = ""
    label_q: str = ""
    pos: List[float] = field(default_factory=lambda: [0.0, 0.0])
    scale: float = 1.0


def parse(line: str) -> Optional[RhombusDiagram]:
    def get_num(key):
        m = re.search(rf'\b{key}:\s*(-?[\d.]+)', line)
        return float(m.group(1)) if m else None

    def get_str(key):
        m = re.search(rf'\b{key}[=:]\s*"([^"]*)"', line)
        if m:
            return m.group(1)
        m = re.search(rf'\b{key}[=:]\s*([^,)\s]+)', line)
        return m.group(1) if m else ""

    p = get_num("p")
    q = get_num("q")
    if p is None or q is None:
        return None

    pos_match = re.search(r'\bpos:\s*\(\s*(-?[\d.]+)\s*,\s*(-?[\d.]+)\s*\)', line)
    pos = [float(pos_match.group(1)), float(pos_match.group(2))] if pos_match else [0.0, 0.0]
    scale = get_num("scale") or 1.0

    labels_match = re.search(r'\blabels:\s*(true|false)', line)
    labels = (labels_match.group(1) != "false") if labels_match else False

    label_p = get_str("label_p") or (_fmt(p) if labels else "")
    label_q = get_str("label_q") or (_fmt(q) if labels else "")

    return RhombusDiagram(p=p, q=q, labels=labels, label_p=label_p, label_q=label_q,
                          pos=pos, scale=scale)


def render(d: RhombusDiagram, viz_scale: float = None) -> str:
    p = d.p * d.scale   # horizontal diagonal
    q = d.q * d.scale   # vertical diagonal
    cx0, cy0 = d.pos

    # Vertices: top, right, bottom, left (SVG: y increases downward)
    sTop_x,  sTop_y  = cx0,       cy0 - q / 2
    sRgt_x,  sRgt_y  = cx0 + p/2, cy0
    sBtm_x,  sBtm_y  = cx0,       cy0 + q / 2
    sLft_x,  sLft_y  = cx0 - p/2, cy0

    if viz_scale is None:
        content_span = max(p, q * (60.0 / 36.0))
        expected_vw  = content_span / 0.92
        viz_scale    = expected_vw / 60.0

    sw        = 0.192 * viz_scale
    font_size = 2.0   * viz_scale
    ra_size   = 2.0   * viz_scale
    out = []

    # Rhombus outline
    pts = (f"{sTop_x:.3f},{sTop_y:.3f} {sRgt_x:.3f},{sRgt_y:.3f} "
           f"{sBtm_x:.3f},{sBtm_y:.3f} {sLft_x:.3f},{sLft_y:.3f}")
    out.append(
        f'<polygon points="{pts}" fill="none" stroke="black" '
        f'stroke-width="{sw}" stroke-linejoin="round" stroke-linecap="round"/>'
    )

    # Equal-side tick marks — single tick on all four sides
    tick_size  = 1.1 * viz_scale
    tick_sw    = 0.14 * viz_scale
    out.append(_tick_mark(sTop_x, sTop_y, sRgt_x, sRgt_y, 1, tick_size, tick_sw))
    out.append(_tick_mark(sRgt_x, sRgt_y, sBtm_x, sBtm_y, 1, tick_size, tick_sw))
    out.append(_tick_mark(sBtm_x, sBtm_y, sLft_x, sLft_y, 1, tick_size, tick_sw))
    out.append(_tick_mark(sLft_x, sLft_y, sTop_x, sTop_y, 1, tick_size, tick_sw))
    # Parallel-side arrows — offset to t=0.35 so they don't overlap the midpoint ticks
    arrow_size = 1.0 * viz_scale
    out.append(_parallel_arrow(sTop_x, sTop_y, sRgt_x, sRgt_y, 1, arrow_size, tick_sw, t=0.35))
    out.append(_parallel_arrow(sLft_x, sLft_y, sBtm_x, sBtm_y, 1, arrow_size, tick_sw, t=0.35))
    out.append(_parallel_arrow(sRgt_x, sRgt_y, sBtm_x, sBtm_y, 2, arrow_size, tick_sw, t=0.35))
    out.append(_parallel_arrow(sTop_x, sTop_y, sLft_x, sLft_y, 2, arrow_size, tick_sw, t=0.35))

    # Diagonals (dotted)
    dash = f"{sw * 3:.2f},{sw * 2:.2f}"
    # Horizontal diagonal
    out.append(
        f'<line x1="{sLft_x:.3f}" y1="{sLft_y:.3f}" x2="{sRgt_x:.3f}" y2="{sRgt_y:.3f}" '
        f'stroke="black" stroke-width="{sw}" stroke-dasharray="{dash}" stroke-linecap="round"/>'
    )
    # Vertical diagonal
    out.append(
        f'<line x1="{sTop_x:.3f}" y1="{sTop_y:.3f}" x2="{sBtm_x:.3f}" y2="{sBtm_y:.3f}" '
        f'stroke="black" stroke-width="{sw}" stroke-dasharray="{dash}" stroke-linecap="round"/>'
    )

    # Right-angle marker at the centre where diagonals intersect
    # Horizontal goes right (0) and vertical goes down (-π/2 in our convention)
    out.append(_right_angle_marker(cx0, cy0, 0.0, -math.pi / 2, ra_size, sw))

    # Labels suppressed in pass 1 (viz_scale == 1.0) to avoid inflating the bbox
    if viz_scale != 1.0:
        # label_p: 25% from right corner toward left, just below the horizontal diagonal
        if d.label_p:
            lx = cx0 + 0.25 * p
            ly = cy0 + font_size * 0.7
            out.append(_text(lx, ly, d.label_p, font_size))

        # label_q: 25% from bottom corner toward top, just right of the vertical diagonal
        if d.label_q:
            lx = cx0 + font_size * 0.7
            ly = cy0 + 0.25 * q
            out.append(_text(lx, ly, d.label_q, font_size))

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
