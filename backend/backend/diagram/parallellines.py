import re
import math
from dataclasses import dataclass, field
from typing import List, Optional

DIAGRAM_TYPE = "ParallelLines"

# Syntax: ParallelLines(angle: 60, arc_1: 1, arc_2: 0, ..., arc_8: 2, label_1: 60, label_2: ?, ...)
#
# Two horizontal parallel lines cut by a transversal.
# Angle numbering at each intersection (θ = transversal angle from horizontal, measured CCW):
#
#   Line 1 (top):    2 | 1      Line 2 (bottom):  6 | 5
#                   ---|---                       ---|---
#                    3 | 4                         7 | 8
#
#   1/5 = upper-right   2/6 = upper-left
#   3/7 = lower-left    4/8 = lower-right
#
# arc_N: 0 = none, 1 = single arc, 2 = double arc
# label_N: text label for angle region N (e.g. "60", "a", "?")
#
# Vertex labels — 8 named points on the diagram:
#
#              A
#             /
#   B ───── C ─────── D      (top parallel line)
#           /
#          /
#   E ───── F ─────── G      (bottom parallel line)
#           /
#          H
#
# labels: [A, B, C, D, E, F, G, H]   (each entry: empty string, text, or {{ expr }})


@dataclass
class ParallelLinesDiagram:
    angle: float = 60.0          # transversal angle from horizontal, degrees (0 < angle < 180)
    arcs: List[int] = field(default_factory=lambda: [0] * 8)    # arc_1 .. arc_8
    labels: List[str] = field(default_factory=lambda: [""] * 8) # label_1 .. label_8
    vertex_labels: List[str] = field(default_factory=lambda: [""] * 8)  # A..H
    colour: str = ""   # cointerior | corresponding | alternate | vert_opposite
    scale: float = 1.0


# Segment IDs for the colour option:
#   A = top line, left of transversal
#   B = top line, right of transversal
#   C = bottom line, left of transversal
#   D = bottom line, right of transversal
#   E = transversal, above top intersection
#   F = transversal, between intersections
#   G = transversal, below bottom intersection
_COLOUR_SEGMENTS: dict = {
    "cointerior":   {"B", "D", "F"},
    "corresponding": {"B", "D", "F", "G"},
    "alternate":    {"A", "F", "D"},
    "vert_opposite": {"A", "B", "E", "F"},
}
_HI_COLOR = "#f5c516"   # golden yellow


def parse(line: str) -> Optional[ParallelLinesDiagram]:
    def get_num(key):
        m = re.search(rf'\b{key}:\s*(-?[\d.]+)', line)
        return float(m.group(1)) if m else None

    def get_str(key):
        # Match label_N: value  — value is everything up to the next comma or closing paren
        m = re.search(rf'\b{key}:\s*([^,)\s]+)', line)
        return m.group(1) if m else ""

    angle = get_num("angle") or 60.0
    scale = get_num("scale") or 1.0

    # Clamp angle to (0, 180) exclusive
    angle = max(1.0, min(179.0, angle))

    arcs = [int(get_num(f"arc_{i}") or 0) for i in range(1, 9)]
    labels = [get_str(f"label_{i}") for i in range(1, 9)]

    # labels_angle: [A, B, C, ...] — bracket syntax, overrides individual label_N values
    m = re.search(r'\blabels_angle:\s*\[([^\]]*)\]', line)
    if m:
        parts = [p.strip() for p in m.group(1).split(",")]
        for i, p in enumerate(parts[:8]):
            if p:
                labels[i] = p

    # Parse colour / color (accept both spellings)
    colour = get_str("colour") or get_str("color")

    # Parse vertex labels: labels: [A, B, C, D, E, F, G, H]
    vertex_labels = [""] * 8
    m = re.search(r'\blabels:\s*\[([^\]]*)\]', line)
    if m:
        parts = [p.strip() for p in m.group(1).split(",")]
        for i, p in enumerate(parts[:8]):
            vertex_labels[i] = p

    return ParallelLinesDiagram(angle=angle, arcs=arcs, labels=labels,
                                vertex_labels=vertex_labels, colour=colour, scale=scale)


def _arc_svg(cx: float, cy: float, angle_from: float, angle_to: float,
             count: int, sw: float) -> str:
    """Draw count concentric arcs from angle_from to angle_to (math convention, CCW, y-up)."""
    if count <= 0:
        return ""

    BASE_R = 1.8
    GAP_R = 0.7

    # Ensure sweep goes CCW (positive direction in math angles)
    sweep = (angle_to - angle_from) % (2 * math.pi)
    # Use the short arc if > π
    if sweep > math.pi:
        angle_from, angle_to = angle_to, angle_from
        sweep = (2 * math.pi) - sweep

    parts = []
    for i in range(count):
        r = BASE_R + i * GAP_R
        # SVG coords: y is flipped
        x1 = cx + r * math.cos(angle_from)
        y1 = cy - r * math.sin(angle_from)
        x2 = cx + r * math.cos(angle_to)
        y2 = cy - r * math.sin(angle_to)
        large_arc = 1 if sweep > math.pi else 0
        # sweep-flag=0 → CCW in SVG (because y is flipped, this is CCW in math)
        parts.append(
            f'<path d="M{x1:.3f},{y1:.3f} A{r:.3f},{r:.3f} 0 {large_arc},0 {x2:.3f},{y2:.3f}" '
            f'fill="none" stroke="black" stroke-width="{sw * 0.7:.2f}"/>'
        )
    return "\n".join(parts)


def _label_svg(cx: float, cy: float, angle_from: float, angle_to: float,
               text: str, count: int, font_size: float) -> str:
    """Place a text label in the middle of the angular region."""
    if not text:
        return ""

    # Midpoint angle of the region (in math convention)
    sweep = (angle_to - angle_from) % (2 * math.pi)
    if sweep > math.pi:
        # Use the short arc direction
        mid_ang = angle_from - sweep / 2
    else:
        mid_ang = angle_from + sweep / 2

    # Radius: just beyond the outermost arc (or a default if no arcs)
    BASE_R = 1.8
    GAP_R = 0.7
    r = (BASE_R + max(count - 1, 0) * GAP_R) + 1.5

    lx = cx + r * math.cos(mid_ang)
    ly = cy - r * math.sin(mid_ang)  # SVG y-flip

    return (
        f'<text x="{lx:.3f}" y="{ly:.3f}" text-anchor="middle" dominant-baseline="central" '
        f'font-size="{font_size}" font-family="system-ui, -apple-system, sans-serif" fill="#333">{text}</text>'
    )


def render(d: ParallelLinesDiagram) -> str:
    scale = d.scale
    theta = math.radians(d.angle)  # angle of transversal from horizontal (math CCW)

    # Two horizontal parallel lines at y = +line_y and y = -line_y (SVG: y=∓line_y)
    line_y = 6.0 * scale
    half_w = 18.0 * scale   # half-width of the horizontal lines
    trans_ext = 4.0 * scale  # how far the transversal extends beyond each line

    # x-coordinate of transversal at each line (for a line through origin at angle theta)
    # y = line_y  → x = line_y / tan(theta)  (y is math y here)
    # Avoid division by zero for near-vertical transversals
    cot_theta = math.cos(theta) / math.sin(theta)
    x1_int = line_y * cot_theta   # intersection with top line (math y = +line_y)
    x2_int = -line_y * cot_theta  # intersection with bottom line (math y = -line_y)

    # In SVG coordinates: top parallel line is at svg_y = -line_y, bottom at svg_y = +line_y
    # Intersection points in SVG:
    P1 = (x1_int, -line_y)   # top intersection (SVG)
    P2 = (x2_int, +line_y)   # bottom intersection (SVG)

    sw = 0.4
    font_size = 2.0
    out = []

    highlighted = _COLOUR_SEGMENTS.get(d.colour, set())
    hi_sw = sw * 2.5

    def _seg(x1, y1, x2, y2, seg_id):
        if seg_id in highlighted:
            color, width = _HI_COLOR, hi_sw
        else:
            color, width = "black", sw
        return (f'<line x1="{x1:.3f}" y1="{y1:.3f}" x2="{x2:.3f}" y2="{y2:.3f}" '
                f'stroke="{color}" stroke-width="{width:.3f}" stroke-linecap="round"/>')

    # ── Parallel lines (split at transversal intersection) ───────────────────
    # Top line: A = left of P1, B = right of P1
    out.append(_seg(-half_w, -line_y, P1[0], -line_y, "A"))
    out.append(_seg(P1[0],   -line_y, half_w, -line_y, "B"))
    # Bottom line: C = left of P2, D = right of P2
    out.append(_seg(-half_w, line_y, P2[0], line_y, "C"))
    out.append(_seg(P2[0],   line_y, half_w, line_y, "D"))

    # ── Parallel line arrow marks (>> chevrons on each line) ─────────────────
    arrow_cx = -half_w * 0.35 - 3.6 * scale  # centre-x of the double-arrow group
    arrow_w = 0.8 * scale        # fore-aft width of each chevron
    arrow_h = 0.6 * scale        # half-height of each chevron
    arrow_gap = 0.88 * scale     # separation between the two chevrons
    arrow_sw = sw * 0.9
    for svg_y in (-line_y, line_y):
        for dx in (-arrow_gap / 2, arrow_gap / 2):
            tip_x = arrow_cx + dx + arrow_w / 2
            base_x = arrow_cx + dx - arrow_w / 2
            # upper arm
            out.append(
                f'<line x1="{base_x:.3f}" y1="{svg_y - arrow_h:.3f}" '
                f'x2="{tip_x:.3f}" y2="{svg_y:.3f}" '
                f'stroke="black" stroke-width="{arrow_sw}" stroke-linecap="round"/>'
            )
            # lower arm
            out.append(
                f'<line x1="{base_x:.3f}" y1="{svg_y + arrow_h:.3f}" '
                f'x2="{tip_x:.3f}" y2="{svg_y:.3f}" '
                f'stroke="black" stroke-width="{arrow_sw}" stroke-linecap="round"/>'
            )

    # ── Transversal (split into 3 segments) ──────────────────────────────────
    # Direction vector of transversal in SVG coords (y-flipped)
    # Math angle theta → SVG direction: (cos θ, -sin θ)
    dx_unit = math.cos(theta)
    dy_unit = -math.sin(theta)  # SVG y-flip

    # Extend trans_ext beyond each intersection
    t1x = P1[0] + trans_ext * dx_unit
    t1y = P1[1] + trans_ext * dy_unit
    t2x = P2[0] - trans_ext * dx_unit
    t2y = P2[1] - trans_ext * dy_unit

    # E = above top intersection, F = between intersections, G = below bottom
    out.append(_seg(t1x,   t1y,   P1[0], P1[1], "E"))
    out.append(_seg(P1[0], P1[1], P2[0], P2[1], "F"))
    out.append(_seg(P2[0], P2[1], t2x,   t2y,   "G"))

    # ── Angles at each intersection ───────────────────────────────────────────
    # At each intersection the transversal creates 4 angle regions.
    # We define region boundaries using math angles (CCW from +x, y-up):
    #
    #   The transversal goes in direction +θ and -θ (i.e. θ and θ+π)
    #   The horizontal line goes in direction 0 and π
    #
    # 4 regions at each intersection (angles measured CCW from +x):
    #   Region upper-right (1 or 5): from  0     to  θ
    #   Region upper-left  (2 or 6): from  θ     to  π
    #   Region lower-left  (3 or 7): from  π     to  π+θ   (= θ+π, i.e. -θ in [π,2π])
    #   Region lower-right (4 or 8): from  π+θ   to  2π

    regions = [
        (0.0,           theta),           # upper-right  (1/5)
        (theta,         math.pi),         # upper-left   (2/6)
        (math.pi,       math.pi + theta), # lower-left   (3/7)
        (math.pi + theta, 2 * math.pi),   # lower-right  (4/8)
    ]

    intersections = [P1, P2]      # top intersection, bottom intersection
    offsets = [0, 4]              # angles 1-4 at P1, angles 5-8 at P2

    for (cx, cy), base in zip(intersections, offsets):
        for j, (ang_from, ang_to) in enumerate(regions):
            idx = base + j          # 0-indexed (0..7)
            arc_count = d.arcs[idx]
            label_text = d.labels[idx]

            arc_svg = _arc_svg(cx, cy, ang_from, ang_to, arc_count, sw)
            if arc_svg:
                out.append(arc_svg)

            lbl_svg = _label_svg(cx, cy, ang_from, ang_to, label_text, arc_count, font_size)
            if lbl_svg:
                out.append(lbl_svg)

    # ── Vertex labels A..H ────────────────────────────────────────────────────
    # A = above top intersection (along transversal, up)
    # B = left end of top parallel line
    # C = top intersection
    # D = right end of top parallel line
    # E = left end of bottom parallel line
    # F = bottom intersection
    # G = right end of bottom parallel line
    # H = below bottom intersection (along transversal, down)
    lbl_off = 2.2 * scale      # offset distance for endpoint labels
    lbl_fs = font_size * 1.1

    vertex_positions = [
        (P1[0] + trans_ext * dx_unit,       P1[1] + trans_ext * dy_unit),   # A (top of transversal)
        (-half_w,                            -line_y),                         # B (left end, top line)
        P1,                                                                     # C (top intersection)
        (half_w,                             -line_y),                         # D (right end, top line)
        (-half_w,                             line_y),                         # E (left end, bottom line)
        P2,                                                                     # F (bottom intersection)
        (half_w,                              line_y),                         # G (right end, bottom line)
        (P2[0] - trans_ext * dx_unit,        P2[1] - trans_ext * dy_unit),   # H (bottom of transversal)
    ]

    # Outward offset directions for each vertex (so label doesn't overlap the lines)
    # Using (dx, dy) in SVG coords
    perp_up   = (-math.sin(theta),  math.cos(theta))   # perpendicular to transversal, upward in SVG = rotated CCW
    perp_down = ( math.sin(theta), -math.cos(theta))

    vertex_offsets = [
        (dx_unit * lbl_off,      dy_unit * lbl_off),       # A: along transversal away from intersection
        (-lbl_off,               0.0),                       # B: left
        (perp_down[0]*lbl_off,   perp_down[1]*lbl_off),    # C: below-left (away from angle region)
        ( lbl_off,               0.0),                       # D: right
        (-lbl_off,               0.0),                       # E: left
        (perp_down[0]*lbl_off,   perp_down[1]*lbl_off),    # F: below-left
        ( lbl_off,               0.0),                       # G: right
        (-dx_unit * lbl_off,    -dy_unit * lbl_off),        # H: along transversal away from intersection
    ]

    for i, (vx, vy) in enumerate(vertex_positions):
        text = d.vertex_labels[i]
        if not text:
            continue
        ox, oy = vertex_offsets[i]
        lx = vx + ox
        ly = vy + oy
        out.append(
            f'<text x="{lx:.3f}" y="{ly:.3f}" text-anchor="middle" dominant-baseline="central" '
            f'font-size="{lbl_fs}" font-family="system-ui, -apple-system, sans-serif" '
            f'font-style="italic" fill="#222">{text}</text>'
        )

    return "\n".join(p for p in out if p)
