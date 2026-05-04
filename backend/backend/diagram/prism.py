import re
import math
from dataclasses import dataclass, field
from typing import List, Optional

DIAGRAM_TYPE = "Prism"

# Syntax:
#   Prism(sides: [3, 4, 5], depth: 4, labels: true)
#   Prism(sides: [6, 4, 6, 4], depth: 3, labels: true)
#   Prism(sides: [3, 4, 5], depth: 4, label_h: "h")
#   Prism(sides: [3, 4, 5], depth: 4, label_h: "6")
#
# sides: [a, b, c]       → triangular prism (triangle cross-section)
# sides: [w, h, w, h]    → rectangular prism (width × height cross-section)
# depth:   length of the prism
# labels:  true (default) — side lengths on front face + depth on one edge
# label_h: text to display on the triangle height line (e.g. "h" or "6").
#           If set, a dashed perpendicular height line is drawn on the front face
#           from the apex down to the base, with a right-angle marker at the foot.
#           Only applies to triangular prisms.


@dataclass
class PrismDiagram:
    sides: List[float] = field(default_factory=lambda: [3.0, 4.0, 5.0])
    depth: float = 4.0
    labels: bool = True
    label_h: str = ""


def parse(line: str) -> Optional[PrismDiagram]:
    sides_m = re.search(r'\bsides:\s*\[([^\]]*)\]', line)
    if not sides_m:
        return None
    try:
        sides = [float(v.strip()) for v in sides_m.group(1).split(',') if v.strip()]
    except ValueError:
        return None
    if len(sides) not in (3, 4):
        return None
    if len(sides) == 3:
        a, b, c = sides
        if a + b <= c or a + c <= b or b + c <= a:
            return None

    depth_m = re.search(r'\bdepth:\s*([\d.]+)', line)
    depth = float(depth_m.group(1)) if depth_m else 4.0

    labels_m = re.search(r'\blabels:\s*(true|false)', line)
    labels = (labels_m.group(1) != 'false') if labels_m else True

    # label_h: quoted string ("h") or bare word (h)
    lh_m = re.search(r'\blabel_h:\s*"([^"]*)"', line)
    if not lh_m:
        lh_m = re.search(r'\blabel_h:\s*([^,)\s]+)', line)
    label_h = lh_m.group(1) if lh_m else ""

    return PrismDiagram(sides=sides, depth=depth, labels=labels, label_h=label_h)


def _triangle_verts(a, b, c):
    """Triangle vertices in maths coords (y-up): B origin, C along +x, A above."""
    cos_b = max(-1.0, min(1.0, (a*a + c*c - b*b) / (2*a*c)))
    ax = c * cos_b
    ay = c * math.sqrt(max(0.0, 1.0 - cos_b*cos_b))
    return [(0.0, 0.0), (a, 0.0), (ax, ay)]


def _rect_verts(w, h):
    """Rectangle vertices in maths coords: BL, BR, TR, TL."""
    return [(0.0, 0.0), (w, 0.0), (w, h), (0.0, h)]


def _fmt(n: float) -> str:
    return str(int(n)) if n == int(n) else f"{n:g}"


def _edge_label(x1, y1, x2, y2, cent_x, cent_y, text, font_size):
    """Place label at midpoint of edge, offset outward from centroid."""
    if not text:
        return ""
    mx, my = (x1 + x2) / 2, (y1 + y2) / 2
    dx, dy = x2 - x1, y2 - y1
    length = math.hypot(dx, dy)
    if length == 0:
        return ""
    px, py = -dy / length, dx / length
    if px * (cent_x - mx) + py * (cent_y - my) > 0:
        px, py = -px, -py
    lx = mx + px * font_size * 1.04
    ly = my + py * font_size * 1.04
    return (
        f'<text x="{lx:.3f}" y="{ly:.3f}" font-size="{font_size}" '
        f'font-family="system-ui, -apple-system, sans-serif" text-anchor="middle" dominant-baseline="middle">'
        f'{text}</text>'
    )


def render(d: PrismDiagram) -> str:
    is_tri = len(d.sides) == 3

    # ── Face vertices in maths coords ────────────────────────
    if is_tri:
        a, b, c = d.sides
        verts = _triangle_verts(a, b, c)
        # When a height line is shown, hide the two slant sides — the base remains
        side_labels = [_fmt(a), "" if d.label_h else _fmt(b), "" if d.label_h else _fmt(c)]
    else:
        w, h = d.sides[0], d.sides[1]
        verts = _rect_verts(w, h)
        # Width on bottom, height on left only (right side overlaps back face)
        side_labels = [_fmt(w), "", "", _fmt(h)]

    # ── Scale to ≈ 18 SVG units for the largest face dimension ──
    xs = [v[0] for v in verts]
    ys = [v[1] for v in verts]
    max_dim = max(max(xs) - min(xs), max(ys) - min(ys), 0.1)
    scale = 18.0 / max_dim

    # ── Convert to SVG coords (y-flip + scale) then centre ────
    face = [(v[0] * scale, -v[1] * scale) for v in verts]
    cx_avg = sum(v[0] for v in face) / len(face)
    cy_avg = sum(v[1] for v in face) / len(face)
    face = [(v[0] - cx_avg, v[1] - cy_avg) for v in face]

    # ── Depth offset: 0.7 × depth × scale, right and up ──────
    ox =  d.depth * scale * 0.49
    oy = -d.depth * scale * 0.49   # negative = upward in SVG

    # Shift front face by −½ offset so prism is centred overall
    face = [(v[0] - ox / 2, v[1] - oy / 2) for v in face]
    back = [(v[0] + ox, v[1] + oy) for v in face]

    n  = len(face)
    sw = 0.16
    fs = 2.0
    out = []

    # Front-face centroid (for label outward direction)
    cent_x = sum(v[0] for v in face) / n
    cent_y = sum(v[1] for v in face) / n

    # Determine which vertices are on the visible side of the prism.
    # For a triangle: rightmost vertex and topmost vertex (min y in SVG).
    # For a rectangle: the two rightmost vertices.
    # Connecting edges and back-face edges whose both endpoints are visible → black.
    if is_tri:
        right = max(range(n), key=lambda i: face[i][0])
        top   = min(range(n), key=lambda i: face[i][1])
        visible = {right, top}
    else:
        by_x = sorted(range(n), key=lambda i: face[i][0], reverse=True)
        visible = set(by_x[:2])
        # The top-left vertex (min x, min SVG y) is on the visible top face —
        # its connecting edge and the back-top edge should both be dark.
        top_left = min(range(n), key=lambda i: (face[i][0], face[i][1]))
        visible.add(top_left)

    def edge_stroke(i, j=None):
        j = (i + 1) % n if j is None else j
        return "black" if (i in visible and j in visible) else "#BBB"

    # ── 1. Connecting (depth) edges ───────────────────────────
    for i in range(n):
        fx, fy = face[i]
        bx, by = back[i]
        stroke = "black" if i in visible else "#BBB"
        out.append(
            f'<line x1="{fx:.3f}" y1="{fy:.3f}" x2="{bx:.3f}" y2="{by:.3f}" '
            f'stroke="{stroke}" stroke-width="{sw}" stroke-linecap="round"/>'
        )

    # ── 2. Back face ──────────────────────────────────────────
    for i in range(n):
        x1, y1 = back[i]
        x2, y2 = back[(i + 1) % n]
        out.append(
            f'<line x1="{x1:.3f}" y1="{y1:.3f}" x2="{x2:.3f}" y2="{y2:.3f}" '
            f'stroke="{edge_stroke(i)}" stroke-width="{sw}" stroke-linecap="round"/>'
        )

    # ── 3. Front face ─────────────────────────────────────────
    for i in range(n):
        x1, y1 = face[i]
        x2, y2 = face[(i + 1) % n]
        out.append(
            f'<line x1="{x1:.3f}" y1="{y1:.3f}" x2="{x2:.3f}" y2="{y2:.3f}" '
            f'stroke="black" stroke-width="{sw}" stroke-linecap="round"/>'
        )

    # ── 4. Triangle height line (front face only) ─────────────
    if is_tri and d.label_h:
        # face[0]=B, face[1]=C, face[2]=A (apex)
        # Foot of perpendicular from A to BC:
        #   B and C have the same y in SVG (both at y_math=0), apex has same x.
        apex_x, apex_y = face[2]
        foot_x = apex_x
        foot_y = face[0][1]   # y of the base (B and C share this after transform)

        sq = sw * 8   # right-angle square size

        # Dashed height line
        out.append(
            f'<line x1="{foot_x:.3f}" y1="{foot_y:.3f}" '
            f'x2="{apex_x:.3f}" y2="{apex_y:.3f}" '
            f'stroke="black" stroke-width="{sw}" '
            f'stroke-dasharray="{sw*6:.2f},{sw*4:.2f}" stroke-linecap="round"/>'
        )

        # Right-angle square at foot (base goes right +x, height goes up −y in SVG)
        # Determine base direction (B→C in SVG)
        bx_svg, by_svg = face[0]
        cx_svg, cy_svg = face[1]
        bdx, bdy = cx_svg - bx_svg, cy_svg - by_svg
        blen = math.hypot(bdx, bdy)
        if blen > 0:
            bux, buy = bdx / blen, bdy / blen   # unit along base
            # Height direction: from foot toward apex
            hlen = abs(apex_y - foot_y)
            if hlen > 0:
                hux = 0.0
                huy = (apex_y - foot_y) / hlen  # unit along height in SVG

                p1x = foot_x + bux * sq;   p1y = foot_y + buy * sq
                p2x = foot_x + hux * sq;   p2y = foot_y + huy * sq
                p3x = p1x + hux * sq;      p3y = p1y + huy * sq
                out.append(
                    f'<path d="M{p1x:.3f},{p1y:.3f} L{p3x:.3f},{p3y:.3f} '
                    f'L{p2x:.3f},{p2y:.3f}" '
                    f'fill="none" stroke="black" stroke-width="{sw:.3f}" '
                    f'stroke-linejoin="miter" stroke-linecap="butt"/>'
                )

        # Height label: 25% of the way up from the foot
        mid_y = foot_y + (apex_y - foot_y) * 0.25
        offset_dir = -1.0 if foot_x < cent_x else 1.0
        lx = foot_x + offset_dir * fs * 1.3
        out.append(
            f'<text x="{lx:.3f}" y="{mid_y:.3f}" font-size="{fs}" '
            f'font-family="system-ui, -apple-system, sans-serif" text-anchor="middle" dominant-baseline="middle">'
            f'{d.label_h}</text>'
        )

    # ── 5. Side and depth labels ──────────────────────────────
    if d.labels:
        for i in range(n):
            x1, y1 = face[i]
            x2, y2 = face[(i + 1) % n]
            out.append(_edge_label(x1, y1, x2, y2, cent_x, cent_y,
                                   side_labels[i] if i < len(side_labels) else "",
                                   fs))

        # Depth label on the rightmost connecting edge
        right_idx = max(range(n), key=lambda i: face[i][0])
        fx, fy = face[right_idx]
        bx, by = back[right_idx]
        mx, my = (fx + bx) / 2, (fy + by) / 2
        edx, edy = bx - fx, by - fy
        elen = math.hypot(edx, edy)
        if elen > 0:
            px, py = -edy / elen, edx / elen
            if px * (cent_x - mx) + py * (cent_y - my) > 0:
                px, py = -px, -py
            out.append(
                f'<text x="{mx + px * fs * 1.04:.3f}" y="{my + py * fs * 1.04:.3f}" '
                f'font-size="{fs}" font-family="system-ui, -apple-system, sans-serif" '
                f'text-anchor="middle" dominant-baseline="middle">'
                f'{_fmt(d.depth)}</text>'
            )

    return "\n".join(p for p in out if p)
