
import re
import math
from dataclasses import dataclass, field
from typing import Optional, Tuple, List

DIAGRAM_TYPE = "GraphLine"

# Syntax:
#   GraphLine(points: [("Jan", 12), ("Feb", 8), ...], y_label: "Rainfall (mm)")
#   GraphLine(points: [(0, 0), (3, 90)], points_2: [(0, 0), (5, 60)], x_label: "Time (hours)", y_label: "Distance (km)")
#   pos: (x, y) is optional (default 0, 0)

@dataclass
class GraphLineDiagram:
    type: str
    points: List[Tuple[str, float]]
    points_2: List[Tuple[str, float]] = field(default_factory=list)
    pos: Tuple[float, float] = (0.0, 0.0)
    x_label: str = ""
    y_label: str = ""
    show_values: bool = True


# Accept pairs like ("Label", 12.3) or (0, 45); allow straight or curly quotes.
# Group 1: quoted label content, Group 2: numeric label, Group 3: value
PAIR_REGEX = re.compile(
    r'\(\s*(?:["\u201c\u201d](.*?)["\u201c\u201d]|(-?\d+(?:\.\d*)?))\s*,\s*(-?\d+(?:\.\d*)?)\s*\)'
)


def _parse_points(segment: str) -> List[Tuple[str, float]]:
    points = []
    for quoted_label, numeric_label, value in PAIR_REGEX.findall(segment):
        label = quoted_label if quoted_label else numeric_label
        points.append((label, float(value)))
    return points


def parse(line: str) -> Optional[GraphLineDiagram]:
    if not line.startswith("GraphLine"):
        return None

    # Parse points_2 first (longer key) so it isn't consumed by the points: match
    pts2_match = re.search(r'points_2:\s*\[(.+?)\]', line)
    pts_match  = re.search(r'(?<!_2)points:\s*\[(.+?)\]', line)

    if not pts_match:
        return None

    points   = _parse_points(pts_match.group(1))
    points_2 = _parse_points(pts2_match.group(1)) if pts2_match else []

    if not points:
        return None

    pos_match = re.search(r'pos:\s*\(\s*(-?[\d.]+)\s*,\s*(-?[\d.]+)\s*\)', line)
    pos = (float(pos_match.group(1)), float(pos_match.group(2))) if pos_match else (0.0, 0.0)

    def _get_label(key):
        m = re.search(rf'{key}:\s*"([^"]*)"', line)
        if m: return m.group(1)
        m = re.search(rf"{key}:\s*''([^'']*)''", line)
        if m: return m.group(1)
        m = re.search(rf"{key}:\s*'([^']*)'", line)
        if m: return m.group(1)
        return ""

    x_label = _get_label("x_label")
    y_label = _get_label("y_label")

    sv_match = re.search(r'\bshow_values:\s*(true|false)', line)
    show_values = (sv_match.group(1) != "false") if sv_match else True

    return GraphLineDiagram(
        type=DIAGRAM_TYPE, points=points, points_2=points_2,
        pos=pos, x_label=x_label, y_label=y_label, show_values=show_values,
    )


def _nice_step(approx: float) -> float:
    if approx <= 0:
        return 1.0
    mag = 10 ** math.floor(math.log10(approx))
    norm = approx / mag
    if norm < 1.5: return mag
    if norm < 3.5: return 2 * mag
    if norm < 7.5: return 5 * mag
    return 10 * mag


def _fmt(n: float) -> str:
    return str(int(n)) if n == int(n) else f"{n:.4g}"


def _try_float(s):
    try:
        return float(s)
    except (ValueError, TypeError):
        return None


# Chart dimensions (SVG units)
_CHART_W = 50.0
_CHART_H = 26.0
_PAD_LEFT   = 8.0   # y-axis tick labels
_PAD_RIGHT  = 4.5
_PAD_TOP    = 4.5   # y_label above arrowhead
_PAD_BOTTOM = 5.0   # x category labels


def viewbox(d: GraphLineDiagram) -> tuple:
    px, py = d.pos
    L = px - _CHART_W / 2
    R = px + _CHART_W / 2
    T = py - _CHART_H / 2
    B = py + _CHART_H / 2
    pad_bottom = (_PAD_BOTTOM + 3.5) if d.x_label else _PAD_BOTTOM
    vb_min_x = L - _PAD_LEFT
    vb_min_y = T - _PAD_TOP
    vb_w = (R + _PAD_RIGHT) - vb_min_x
    vb_h = (B + pad_bottom) - vb_min_y
    return (vb_min_x, vb_min_y, vb_w, vb_h)


def _build_x_pos(all_pts, L):
    """Return a function x_val -> svg_x based on combined numeric x range, or None for even spacing."""
    x_nums = [_try_float(lbl) for lbl, _ in all_pts]
    if all(v is not None for v in x_nums) and len(x_nums) > 1:
        xmin = min(x_nums)
        xmax = max(x_nums)
        x_span = xmax - xmin or 1.0
        return lambda xv: L + (xv - xmin) / x_span * _CHART_W, xmin, xmax
    return None, None, None


def _render_line(frags, pts, x_fn, x_nums_map, y_pos, B, font_size, show_values, color):
    """Render polyline, markers, value labels, and category labels for one series."""
    poly_pts = []
    for i, (lbl, v) in enumerate(pts):
        xv = x_nums_map.get(i) if x_nums_map else None
        x = x_fn(xv) if x_nums_map else x_fn(i)
        poly_pts.append(f"{x:.3f},{y_pos(v):.3f}")
    if poly_pts:
        frags.append(
            f'<polyline fill="none" stroke="{color}" stroke-width="0.8" '
            f'points="{" ".join(poly_pts)}" />'
        )
    for i, (label, v) in enumerate(pts):
        xv = x_nums_map.get(i) if x_nums_map else None
        x = x_fn(xv) if x_nums_map else x_fn(i)
        y = y_pos(v)
        frags.append(f'<circle cx="{x:.3f}" cy="{y:.3f}" r="0.9" fill="{color}" />')
        if show_values:
            frags.append(
                f'<text x="{x:.3f}" y="{y - 1.2:.3f}" font-size="{font_size}" '
                f'text-anchor="middle" fill="#333">{_fmt(v)}</text>'
            )
        frags.append(
            f'<text x="{x:.3f}" y="{B + 3.0:.3f}" font-size="{font_size}" '
            f'text-anchor="middle" fill="#333">{label}</text>'
        )


def render(d: GraphLineDiagram) -> str:
    pts   = d.points
    pts2  = d.points_2
    px, py = d.pos

    all_pts = pts + pts2

    # Y range across both series (always starts at 0)
    max_val = max((v for _, v in all_pts), default=0.0)
    vmin = 0.0
    vmax = max_val if max_val != vmin else vmin + 1.0

    L = px - _CHART_W / 2
    R = px + _CHART_W / 2
    T = py - _CHART_H / 2
    B = py + _CHART_H / 2

    # Build shared x mapping from combined point set
    x_fn_val, xmin_data, xmax_data = _build_x_pos(all_pts, L)

    if x_fn_val is not None:
        # Numeric x: map a float value to svg x
        def make_x_nums_map(pts_list):
            return {i: _try_float(lbl) for i, (lbl, _) in enumerate(pts_list)}
        x_nums_map_1 = make_x_nums_map(pts)
        x_nums_map_2 = make_x_nums_map(pts2) if pts2 else {}
        x_fn = x_fn_val
    else:
        # Categorical: evenly space using index across the combined set
        n_total = len(all_pts)
        dx = _CHART_W / (n_total - 1) if n_total > 1 else 0.0
        # Assign each unique label an index position
        seen = {}
        for i, (lbl, _) in enumerate(all_pts):
            if lbl not in seen:
                seen[lbl] = len(seen)
        def x_fn(idx):
            return L + idx * dx
        x_nums_map_1 = {i: seen.get(lbl, i) for i, (lbl, _) in enumerate(pts)}
        x_nums_map_2 = {i: seen.get(lbl, i) for i, (lbl, _) in enumerate(pts2)} if pts2 else {}

    def y_pos(value: float) -> float:
        if vmax == vmin:
            return (T + B) / 2.0
        t = (value - vmin) / (vmax - vmin)
        return B - t * (B - T)

    sw       = 0.25
    tick_len = 0.8
    font_size = 1.8
    color_1 = "#e15759"
    color_2 = "#4e79a7"

    frags: List[str] = []

    # Background
    frags.append(
        f'<rect x="{L}" y="{T}" width="{_CHART_W}" height="{_CHART_H}" '
        f'fill="white" stroke="#aaa" stroke-width="{sw}"/>'
    )

    # Y-axis grid lines and ticks
    y_step = _nice_step((vmax - vmin) / 6)
    y_grid_start = math.ceil(vmin / y_step) * y_step

    y = y_grid_start
    while y <= vmax + y_step * 0.01:
        sy = y_pos(y)
        frags.append(
            f'<line x1="{L}" y1="{sy:.3f}" x2="{R}" y2="{sy:.3f}" '
            f'stroke="#e0e0e0" stroke-width="{sw}"/>'
        )
        frags.append(
            f'<line x1="{L - tick_len/2:.3f}" y1="{sy:.3f}" '
            f'x2="{L + tick_len/2:.3f}" y2="{sy:.3f}" '
            f'stroke="black" stroke-width="{sw}"/>'
        )
        frags.append(
            f'<text x="{L - tick_len - 0.3:.3f}" y="{sy + font_size*0.35:.3f}" '
            f'text-anchor="end" font-size="{font_size}" '
            f'font-family="system-ui, -apple-system, sans-serif" fill="#333">{_fmt(y)}</text>'
        )
        y += y_step

    # X-axis line
    frags.append(
        f'<line x1="{L}" y1="{B}" x2="{R}" y2="{B}" '
        f'stroke="black" stroke-width="{sw}"/>'
    )

    # Y-axis line with arrowhead
    aw, ah = 0.7, 1.2
    frags.append(
        f'<line x1="{L}" y1="{B}" x2="{L}" y2="{T}" '
        f'stroke="black" stroke-width="{sw}"/>'
    )
    frags.append(
        f'<polygon points="{L},{T} {L - aw/2:.3f},{T + ah} {L + aw/2:.3f},{T + ah}" '
        f'fill="black"/>'
    )

    # Y-axis label
    if d.y_label:
        frags.append(
            f'<text x="{L - 4.6:.3f}" y="{T - 1.8:.3f}" '
            f'text-anchor="start" font-size="{font_size}" '
            f'font-family="system-ui, -apple-system, sans-serif" fill="#333">{d.y_label}</text>'
        )

    # X-axis label
    if d.x_label:
        frags.append(
            f'<text x="{(L + R) / 2:.3f}" y="{B + 7.5:.3f}" '
            f'text-anchor="middle" font-size="{font_size}" '
            f'font-family="system-ui, -apple-system, sans-serif" fill="#333">{d.x_label}</text>'
        )

    # Lines
    _render_line(frags, pts,  x_fn, x_nums_map_1, y_pos, B, font_size, d.show_values, color_1)
    if pts2:
        _render_line(frags, pts2, x_fn, x_nums_map_2, y_pos, B, font_size, d.show_values, color_2)

    return "\n".join(frags)
