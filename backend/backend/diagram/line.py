import re
import math
from dataclasses import dataclass, field
from typing import Tuple, Optional

DIAGRAM_TYPE = "Line"
SUPPORTS_VIZ_SCALE = True

# Syntax:
#   Line(a: (0,0), b: (5,3))
#   Line(a: (0,0), b: (5,3), mode: "Ray")    -- extend beyond b with arrow
#   Line(a: (0,0), b: (5,3), mode: "Line")   -- extend both ends with arrows
#
# a, b: endpoints in standard math coordinates (y-up; converted to SVG y-down internally)
# mode: "Segment" (default) | "Ray" | "Line"
# label_a / label_b: optional text labels near each endpoint circle
# label_m: optional text label at the midpoint (above the line)
#
# Open circles mark the defined endpoints a and b.

_EXT_FRAC = 0.40   # each extension = 40% of the a→b segment length


@dataclass
class LineDiagram:
    a: Tuple[float, float] = (0.0, 0.0)
    b: Tuple[float, float] = (5.0, 0.0)
    mode: str = "Segment"
    label_a: str = ""
    label_b: str = ""
    label_m: str = ""


def parse(line: str) -> Optional[LineDiagram]:
    def get_point(key):
        m = re.search(rf'\b{key}:\s*\(\s*(-?[\d.]+)\s*,\s*(-?[\d.]+)\s*\)', line)
        return (float(m.group(1)), float(m.group(2))) if m else None

    def get_str(key):
        m = re.search(rf'\b{key}[=:]\s*"([^"]*)"', line)
        if m:
            return m.group(1)
        m = re.search(rf'\b{key}[=:]\s*([^,)\s]+)', line)
        return m.group(1) if m else ""

    a = get_point("a")
    b = get_point("b")
    if a is None or b is None:
        return None

    mode_m = re.search(r'\bmode:\s*"([^"]*)"', line)
    mode = mode_m.group(1) if mode_m else "Segment"
    if mode not in ("Segment", "Ray", "Line"):
        mode = "Segment"

    return LineDiagram(
        a=a, b=b, mode=mode,
        label_a=get_str("label_a"),
        label_b=get_str("label_b"),
        label_m=get_str("label_m"),
    )


def render(d: LineDiagram, viz_scale: float = None) -> str:
    ax_m, ay_m = d.a
    bx_m, by_m = d.b

    dx_m = bx_m - ax_m
    dy_m = by_m - ay_m
    length_m = math.hypot(dx_m, dy_m)
    if length_m < 1e-9:
        return ""

    # Unit vector; convert to SVG coords (y-flip)
    ux_m, uy_m = dx_m / length_m, dy_m / length_m
    ax, ay = ax_m, -ay_m
    bx, by = bx_m, -by_m
    ux, uy = ux_m, -uy_m   # unit vector in SVG space

    ext = length_m * _EXT_FRAC

    # Extended endpoints in SVG coords
    head_x = bx + ux * ext;  head_y = by + uy * ext   # beyond b
    tail_x = ax - ux * ext;  tail_y = ay - uy * ext   # behind a

    # Drawn line start / end
    if d.mode == "Segment":
        lx1, ly1 = ax, ay
        lx2, ly2 = bx, by
    elif d.mode == "Ray":
        lx1, ly1 = ax, ay
        lx2, ly2 = head_x, head_y
    else:  # Line
        lx1, ly1 = tail_x, tail_y
        lx2, ly2 = head_x, head_y

    if viz_scale is None:
        pts_x = [ax, bx, lx1, lx2]
        pts_y = [ay, by, ly1, ly2]
        content_w = max(pts_x) - min(pts_x)
        content_h = max(pts_y) - min(pts_y)
        content_span = max(content_w, content_h * (60.0 / 36.0), 1.0)
        expected_vw  = content_span / 0.92
        viz_scale    = expected_vw / 60.0

    sw        = 0.192 * viz_scale
    font_size = 2.0   * viz_scale
    cr        = 1.1   * viz_scale   # endpoint circle radius
    arrow_len = 3.0   * viz_scale   # arrowhead length
    arrow_hw  = 1.1   * viz_scale   # arrowhead half-width

    out = []

    # ── Main line ─────────────────────────────────────────────────────────────
    out.append(
        f'<line x1="{lx1:.3f}" y1="{ly1:.3f}" x2="{lx2:.3f}" y2="{ly2:.3f}" '
        f'stroke="black" stroke-width="{sw}" stroke-linecap="round"/>'
    )

    # ── Arrowhead(s) — drawn over line tips ───────────────────────────────────
    if d.mode in ("Ray", "Line"):
        out.append(_arrowhead(head_x, head_y,  ux,  uy, arrow_len, arrow_hw))
    if d.mode == "Line":
        out.append(_arrowhead(tail_x, tail_y, -ux, -uy, arrow_len, arrow_hw))

    # ── Endpoint circles (drawn on top of the line) ───────────────────────────
    for cx, cy in [(ax, ay), (bx, by)]:
        out.append(
            f'<circle cx="{cx:.3f}" cy="{cy:.3f}" r="{cr:.3f}" '
            f'fill="white" stroke="black" stroke-width="{sw}"/>'
        )

    # ── Labels (suppressed in pass 1 to avoid bbox inflation) ────────────────
    if viz_scale != 1.0:
        # Perpendicular direction: 90° CCW from line direction in SVG
        px_perp, py_perp = -uy, ux
        off = font_size * 1.4

        if d.label_a:
            lax = ax + px_perp * off - ux * off * 0.3
            lay = ay + py_perp * off - uy * off * 0.3
            out.append(_text(lax, lay, d.label_a, font_size))

        if d.label_b:
            lbx = bx + px_perp * off + ux * off * 0.3
            lby = by + py_perp * off + uy * off * 0.3
            out.append(_text(lbx, lby, d.label_b, font_size))

        if d.label_m:
            mx = (ax + bx) / 2 + px_perp * off * 0.75
            my = (ay + by) / 2 + py_perp * off * 0.75
            out.append(_text(mx, my, d.label_m, font_size))

    return "\n".join(p for p in out if p)


# ── Helpers ───────────────────────────────────────────────────────────────────

def _arrowhead(tip_x, tip_y, ux, uy, arrow_len, arrow_hw):
    """Filled triangle arrowhead with tip at (tip_x, tip_y) pointing in (ux, uy)."""
    bcx = tip_x - ux * arrow_len
    bcy = tip_y - uy * arrow_len
    px, py = -uy, ux   # perpendicular unit vector
    w1x = bcx + px * arrow_hw;  w1y = bcy + py * arrow_hw
    w2x = bcx - px * arrow_hw;  w2y = bcy - py * arrow_hw
    return (
        f'<polygon points="{tip_x:.3f},{tip_y:.3f} {w1x:.3f},{w1y:.3f} {w2x:.3f},{w2y:.3f}" '
        f'fill="black" stroke="none"/>'
    )


def _text(x, y, text, font_size):
    return (
        f'<text x="{x:.3f}" y="{y:.3f}" font-size="{font_size}" '
        f'font-family="system-ui, -apple-system, sans-serif" '
        f'text-anchor="middle" dominant-baseline="middle">{text}</text>'
    )
