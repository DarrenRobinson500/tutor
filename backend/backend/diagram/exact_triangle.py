import re
import math
from dataclasses import dataclass
from typing import Optional, Tuple

DIAGRAM_TYPE = "ExactTriangle"
SUPPORTS_VIZ_SCALE = True

_FONT    = "system-ui, -apple-system, sans-serif"
_C_BLUE  = "#2563eb"   # sin  — opposite + hypotenuse
_C_GREEN = "#16a34a"   # cos  — adjacent + hypotenuse
_C_ORA   = "#ea580c"   # tan  — opposite + adjacent
_C_NORM  = "#334155"   # default side colour
_C_ARC   = "#475569"   # angle arc and label
_C_RA    = "#94a3b8"   # right-angle marker


@dataclass
class ExactTriangleDiagram:
    triangle:        str            # "30_60_90" | "45_45_90"
    highlight_angle: Optional[int]  # 30 | 45 | 60 | 90 | None
    label_sides:     bool
    show_ratios:     Optional[str]  # "sin" | "cos" | "tan" | None


def _parse_triangle_id(raw: str) -> Optional[str]:
    """Normalise triangle identifier, tolerating YAML 1.1 integer mangling.

    YAML 1.1 treats underscores as digit separators in numeric-looking values,
    so ``45_45_90`` is silently coerced to the integer ``454590`` before the
    diagram string is assembled.  Strip all separators and match by digit run.
    """
    digits = re.sub(r'[_\-]', '', raw)
    if digits == '306090':
        return '30_60_90'
    if digits == '454590':
        return '45_45_90'
    return None


def parse(line: str) -> Optional[ExactTriangleDiagram]:
    tri_m = re.search(r'\btriangle:\s*([\d_\-]+)', line)
    if not tri_m:
        return None
    triangle = _parse_triangle_id(tri_m.group(1))
    if not triangle:
        return None

    angle_m = re.search(r'\bhighlight_angle:\s*(\d+)', line)
    label_m = re.search(r'\blabel_sides:\s*(true|false)', line)
    ratio_m = re.search(r'\bshow_ratios:\s*(sin|cos|tan)', line)

    return ExactTriangleDiagram(
        triangle=triangle,
        highlight_angle=int(angle_m.group(1)) if angle_m else None,
        label_sides=(label_m.group(1) == 'true') if label_m else True,
        show_ratios=ratio_m.group(1) if ratio_m else None,
    )


# ── Geometry helpers ──────────────────────────────────────────────────────────

def _norm(dx: float, dy: float) -> Tuple[float, float]:
    l = math.hypot(dx, dy)
    return (dx / l, dy / l) if l > 0 else (1.0, 0.0)


def _arc_path(vx: float, vy: float,
               p1x: float, p1y: float,
               p2x: float, p2y: float, r: float) -> str:
    """SVG arc centred at (vx, vy), sweeping through the interior angle."""
    d1 = _norm(p1x - vx, p1y - vy)
    d2 = _norm(p2x - vx, p2y - vy)
    sx, sy = vx + r * d1[0], vy + r * d1[1]
    ex, ey = vx + r * d2[0], vy + r * d2[1]
    # Cross product in SVG (y-down): negative → clockwise sweep is the interior arc.
    cross  = d1[0] * d2[1] - d1[1] * d2[0]
    sweep  = 0 if cross <= 0 else 1
    return f'M{sx:.3f},{sy:.3f} A{r:.3f},{r:.3f} 0 0,{sweep} {ex:.3f},{ey:.3f}'


def _bisector(vx: float, vy: float,
               p1x: float, p1y: float,
               p2x: float, p2y: float) -> Tuple[float, float]:
    """Unit bisector pointing into the interior angle at (vx, vy)."""
    d1 = _norm(p1x - vx, p1y - vy)
    d2 = _norm(p2x - vx, p2y - vy)
    return _norm(d1[0] + d2[0], d1[1] + d2[1])


def _geometry(triangle: str):
    """Centered triangle vertices and side labels.

    Returns (A, B, C, side_labels) where B is the right-angle vertex.
    Layout for both triangles:
      A = smaller angle, left
      B = 90°, bottom-right
      C = larger/other angle, top-right (directly above B)
    """
    S = 12.0
    if triangle == '30_60_90':
        # A = 30° (left),  B = 90° (bottom-right),  C = 60° (top-right)
        # Side AB (bottom horizontal, length √3) is opposite 60°.
        # Side BC (right vertical, length 1) is opposite 30°.
        # Side AC (hypotenuse, length 2).
        raw_A = (-S * math.sqrt(3), 0.0)
        raw_B = (0.0, 0.0)
        raw_C = (0.0, -S)
        side_labels = {'AB': '√3', 'BC': '1', 'AC': '2'}
    else:  # 45_45_90
        # A = 45° (left),  B = 90° (bottom-right),  C = 45° (top-right)
        raw_A = (-S,  0.0)
        raw_B = (0.0, 0.0)
        raw_C = (0.0, -S)
        side_labels = {'AB': '1', 'BC': '1', 'AC': '√2'}

    cx = (raw_A[0] + raw_B[0] + raw_C[0]) / 3
    cy = (raw_A[1] + raw_B[1] + raw_C[1]) / 3
    A = (raw_A[0] - cx, raw_A[1] - cy)
    B = (raw_B[0] - cx, raw_B[1] - cy)
    C = (raw_C[0] - cx, raw_C[1] - cy)
    return A, B, C, side_labels


def _side_colours(triangle: str, highlight_angle: Optional[int],
                   show_ratios: Optional[str]) -> dict:
    """Return {side_name: colour} for the two sides involved in the ratio."""
    if not show_ratios:
        return {}

    if triangle == '30_60_90':
        if highlight_angle == 30:
            opp, adj, hyp = 'BC', 'AB', 'AC'
        elif highlight_angle == 60:
            opp, adj, hyp = 'AB', 'BC', 'AC'
        else:
            return {}
    else:  # 45_45_90 — A is the reference vertex (left); opp=BC, adj=AB
        opp, adj, hyp = 'BC', 'AB', 'AC'

    if show_ratios == 'sin':
        return {opp: _C_BLUE,  hyp: _C_BLUE}
    if show_ratios == 'cos':
        return {adj: _C_GREEN, hyp: _C_GREEN}
    if show_ratios == 'tan':
        return {opp: _C_ORA,   adj: _C_ORA}
    return {}


# ── Engine interface ──────────────────────────────────────────────────────────

def viewbox(d: ExactTriangleDiagram) -> tuple:
    A, B, C, _ = _geometry(d.triangle)
    xs = [A[0], B[0], C[0]]
    ys = [A[1], B[1], C[1]]
    pad = 9.0
    x0 = min(xs) - pad
    y0 = min(ys) - pad
    w  = max(xs) - min(xs) + 2 * pad
    h  = max(ys) - min(ys) + 2 * pad
    # Shrink viewbox by 20% (zoom in), keeping it centred on the content
    cx, cy = x0 + w / 2, y0 + h / 2
    w *= 0.8
    h *= 0.8
    return (cx - w / 2, cy - h / 2, w, h)


def render(d: ExactTriangleDiagram, viz_scale: float = 1.0) -> str:
    A, B, C, side_labels = _geometry(d.triangle)
    colours = _side_colours(d.triangle, d.highlight_angle, d.show_ratios)

    sw      = 0.35 * viz_scale
    fs      = 2.2  * viz_scale
    arc_r   = 6.6  * viz_scale
    sq_size = 1.5  * viz_scale

    # For 30-60-90: A=30° (left), B=90° (bottom-right), C=60° (top-right)
    # For 45-45-90: A=45° (left), B=90° (bottom-right), C=45° (top-right)
    if d.triangle == '30_60_90':
        angle_verts = {
            30: (A, B, C),
            60: (C, A, B),
            90: (B, A, C),
        }
    else:
        angle_verts = {
            45: (A, B, C),
            90: (B, A, C),
        }

    out = []

    # ── Sides ─────────────────────────────────────────────────────────────────
    sides = [('AB', A, B), ('BC', B, C), ('AC', A, C)]
    for name, p1, p2 in sides:
        col       = colours.get(name, _C_NORM)
        thickness = sw * 0.9
        out.append(
            f'<line x1="{p1[0]:.3f}" y1="{p1[1]:.3f}" '
            f'x2="{p2[0]:.3f}" y2="{p2[1]:.3f}" '
            f'stroke="{col}" stroke-width="{thickness:.3f}" stroke-linecap="round"/>'
        )

    # ── Right-angle marker at B ────────────────────────────────────────────────
    da  = _norm(A[0] - B[0], A[1] - B[1])
    dc  = _norm(C[0] - B[0], C[1] - B[1])
    sq1 = (B[0] + sq_size * da[0],                   B[1] + sq_size * da[1])
    sq2 = (B[0] + sq_size * da[0] + sq_size * dc[0], B[1] + sq_size * da[1] + sq_size * dc[1])
    sq3 = (B[0] + sq_size * dc[0],                   B[1] + sq_size * dc[1])
    out.append(
        f'<polyline points="{sq1[0]:.3f},{sq1[1]:.3f} '
        f'{sq2[0]:.3f},{sq2[1]:.3f} '
        f'{sq3[0]:.3f},{sq3[1]:.3f}" '
        f'fill="none" stroke="{_C_RA}" stroke-width="{sw:.3f}"/>'
    )

    # ── Arc and label at highlight_angle ──────────────────────────────────────
    ha = d.highlight_angle
    if ha and ha != 90 and ha in angle_verts:
        vert, adj1, adj2 = angle_verts[ha]
        arc = _arc_path(vert[0], vert[1], adj1[0], adj1[1], adj2[0], adj2[1], arc_r)
        out.append(
            f'<path d="{arc}" fill="none" stroke="{_C_ARC}" stroke-width="{sw:.3f}"/>'
        )
        bx, by = _bisector(vert[0], vert[1], adj1[0], adj1[1], adj2[0], adj2[1])
        lx = vert[0] + (arc_r + 2.2 * viz_scale) * bx
        ly = vert[1] + (arc_r + 2.2 * viz_scale) * by
        out.append(
            f'<text x="{lx:.3f}" y="{ly:.3f}" font-size="{fs:.3f}" '
            f'font-family="{_FONT}" text-anchor="middle" dominant-baseline="middle" '
            f'fill="{_C_ARC}">{ha}°</text>'
        )

    # ── Side labels ───────────────────────────────────────────────────────────
    if d.label_sides:
        label_off = 2.8 * viz_scale
        for name, p1, p2 in sides:
            label = side_labels.get(name, '')
            if not label:
                continue
            col = colours.get(name, _C_NORM)
            mx, my = (p1[0] + p2[0]) / 2, (p1[1] + p2[1]) / 2
            # Outward normal: perpendicular to the side, away from centroid (origin)
            dx, dy = _norm(p2[0] - p1[0], p2[1] - p1[1])
            nx, ny = -dy, dx
            if nx * mx + ny * my < 0:
                nx, ny = -nx, -ny
            lx, ly = mx + label_off * nx, my + label_off * ny
            out.append(
                f'<text x="{lx:.3f}" y="{ly:.3f}" font-size="{fs:.3f}" '
                f'font-family="{_FONT}" text-anchor="middle" dominant-baseline="middle" '
                f'fill="{col}">{label}</text>'
            )

    return '\n'.join(out)
