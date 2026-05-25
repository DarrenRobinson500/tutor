import re
import math
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

DIAGRAM_TYPE = "CircleTheorem"
SUPPORTS_VIZ_SCALE = True

# Syntax:
# CircleTheorem(
#   radius: 5,
#   points: {O: centre, A: 40, B: 160, C: 260, P: (0, 14), Q: AB CD},
#   lines: [OA, OB, AB, AC, BC, tangentA],
#   highlight_arc: AB,
#   label_angle: {AOB: "2x", ACB: "?"},
#   midpoint: {M: AB},
#   right_angle_at: [T],
#   label_length: {OP: "r cm", OM: "d cm", PQ: "?"}
# )
#
# • points        — named points. Four value forms:
#                     centre      → at the circle centre
#                     <number>    → on circumference, degrees CCW from 3 o'clock
#                     (x, y)      → explicit SVG coords (origin = circle centre,
#                                   circle radius is always 10 SVG units)
#                     AB CD       → intersection of segment AB and segment CD
# • lines         — two-letter pairs drawn as straight segments;
#                   'tangentX' draws a tangent at circumference point X
# • highlight_arc — highlights the minor arc between two named points
# • label_angle   — angle arc + label; middle letter is vertex (e.g. AOB → arc at O)
# • right_angle_at— small square marker at each named point
# • label_length  — label at segment midpoint, offset perpendicularly outward


@dataclass
class CircleTheoremDiagram:
    radius:         float             = 5.0
    points:         Dict[str, object] = field(default_factory=dict)
    lines:          List[str]         = field(default_factory=list)
    tangent_at:     List[str]         = field(default_factory=list)
    highlight_arc:  str               = ""
    label_angle:    Dict[str, str]    = field(default_factory=dict)
    right_angle_at: List[str]         = field(default_factory=list)
    label_length:   Dict[str, str]    = field(default_factory=dict)
    midpoint:       Dict[str, str]    = field(default_factory=dict)


# ── Helpers ───────────────────────────────────────────────────────────────────

def _pt(r: float, deg: float) -> Tuple[float, float]:
    """SVG point at angle deg (CCW from 3 o'clock, y-flipped for SVG)."""
    rad = math.radians(deg)
    return r * math.cos(rad), -r * math.sin(rad)


def _math_angle(ox: float, oy: float, px: float, py: float) -> float:
    """Math angle (CCW from +x) in degrees of vector O→P in SVG coords."""
    return math.degrees(math.atan2(-(py - oy), px - ox))


def _extract_braced(text: str, key: str) -> Optional[str]:
    """Return content inside the first { } block following 'key:'."""
    m = re.search(rf'\b{re.escape(key)}\s*:\s*\{{', text)
    if not m:
        return None
    start = m.end() - 1
    depth = 0
    for i in range(start, len(text)):
        if text[i] == '{':
            depth += 1
        elif text[i] == '}':
            depth -= 1
            if depth == 0:
                return text[start + 1:i]
    return None


def _line_intersect(
    x1: float, y1: float, x2: float, y2: float,
    x3: float, y3: float, x4: float, y4: float,
) -> Optional[Tuple[float, float]]:
    """Intersection of lines (x1,y1)-(x2,y2) and (x3,y3)-(x4,y4). None if parallel."""
    dx1, dy1 = x2 - x1, y2 - y1
    dx2, dy2 = x4 - x3, y4 - y3
    det = dx1 * dy2 - dy1 * dx2
    if abs(det) < 1e-9:
        return None
    t = ((x3 - x1) * dy2 - (y3 - y1) * dx2) / det
    return x1 + t * dx1, y1 + t * dy1


def _pt_seg_dist(px: float, py: float,
                 x1: float, y1: float, x2: float, y2: float) -> float:
    """Minimum distance from point (px, py) to segment (x1,y1)-(x2,y2)."""
    dx, dy = x2 - x1, y2 - y1
    len_sq = dx*dx + dy*dy
    if len_sq < 1e-18:
        return math.hypot(px - x1, py - y1)
    t = max(0.0, min(1.0, ((px - x1)*dx + (py - y1)*dy) / len_sq))
    return math.hypot(px - (x1 + t*dx), py - (y1 + t*dy))


def _clear_label(lx: float, ly: float, ax: float, ay: float,
                 segs: list, threshold: float,
                 obstacles: list = (), obs_threshold: float = 0.0,
                 circle: tuple = ()) -> Tuple[float, float]:
    """
    Return a label position clear of line segments, placed-label obstacles,
    and an optional circle (cx, cy, r).  Uses a normalised score so all
    constraints are balanced; a score >= 1.0 means fully clear.  Rotates the
    offset vector in 30° steps and returns the candidate with the best score.
    """
    def _score(cx: float, cy: float) -> float:
        seg_score = min((_pt_seg_dist(cx, cy, *s) for s in segs), default=math.inf) / threshold
        if obstacles and obs_threshold > 0:
            obs_score = min((math.hypot(cx - px, cy - py)
                             for px, py in obstacles), default=math.inf) / obs_threshold
            seg_score = min(seg_score, obs_score)
        if circle:
            circ_dist = abs(math.hypot(cx - circle[0], cy - circle[1]) - circle[2]) / threshold
            seg_score = min(seg_score, circ_dist)
        return seg_score

    if _score(lx, ly) >= 1.0:
        return lx, ly
    dx, dy = lx - ax, ly - ay
    best_pos, best_score = (lx, ly), _score(lx, ly)
    for deg in range(0, 360, 30):
        rad = math.radians(deg)
        c, s = math.cos(rad), math.sin(rad)
        cx = ax + dx*c - dy*s
        cy = ay + dx*s + dy*c
        sc = _score(cx, cy)
        if sc > best_score:
            best_score, best_pos = sc, (cx, cy)
    return best_pos


def _label_svg(x: float, y: float, text: str, fs: float,
               anchor: str = "middle", fill: str = "#1a1a2e") -> str:
    return (
        f'<text x="{x:.3f}" y="{y:.3f}" font-size="{fs}" '
        f'font-family="system-ui,-apple-system,sans-serif" '
        f'text-anchor="{anchor}" dominant-baseline="middle" fill="{fill}">'
        f'{text}</text>'
    )


# ── Parse ─────────────────────────────────────────────────────────────────────

def _parse_points(content: str) -> Dict[str, object]:
    """
    Parse a points dict body. Supported value forms per key:
      centre / center          → string 'centre'
      <number>                 → float (circumference angle, CCW from 3 o'clock)
      (x, y)                   → tuple[float, float] (explicit SVG coords)
      AB CD                    → tuple[str, str] (intersection of two named segments)
    """
    points: Dict[str, object] = {}
    pos = 0
    while pos < len(content):
        # skip whitespace and commas
        skip = re.match(r'[\s,]*', content[pos:])
        pos += skip.end()
        if pos >= len(content):
            break
        # key:
        km = re.match(r'([A-Za-z]+)\s*:\s*', content[pos:])
        if not km:
            pos += 1
            continue
        key = km.group(1)
        pos += km.end()
        rest = content[pos:]
        # (x, y) — explicit SVG coordinate
        cm = re.match(r'\(\s*([-\d.]+)\s*,\s*([-\d.]+)\s*\)', rest)
        if cm:
            points[key] = (float(cm.group(1)), float(cm.group(2)))
            pos += cm.end()
            continue
        # AB CD or AB tangentX — named segment intersection
        _seg = r'(?:tangent[A-Za-z]+|[A-Za-z]{2})'
        im = re.match(rf'({_seg})\s+({_seg})', rest)
        if im:
            points[key] = (im.group(1), im.group(2))
            pos += im.end()
            continue
        # plain token — centre or angle
        vm = re.match(r'([^\s,}]+)', rest)
        if vm:
            val = vm.group(1)
            if val.lower() in ('centre', 'center'):
                points[key] = 'centre'
            else:
                try:
                    points[key] = float(val)
                except ValueError:
                    pass
            pos += vm.end()
        else:
            pos += 1
    return points


def parse(line: str) -> Optional[CircleTheoremDiagram]:
    if not line.strip().startswith("CircleTheorem"):
        return None
    m = re.match(r'CircleTheorem\s*\((.+)\)\s*$', line.strip(), re.DOTALL)
    if not m:
        return None
    inner = m.group(1)

    rm = re.search(r'\bradius:\s*([\d.]+)', inner)
    radius = float(rm.group(1)) if rm else 5.0

    # points: {O: centre, A: 40, P: (0, 14), Q: AB CD}
    points: Dict[str, object] = {}
    content = _extract_braced(inner, 'points')
    if content:
        points = _parse_points(content)

    # lines: [OA, OB, tangentT] — 'tangentX' draws a tangent at point X
    lm = re.search(r'\blines:\s*\[([^\]]*)\]', inner)
    raw_lines = lm.group(1) if lm else ""
    tangent_pts = re.findall(r'\btangent([A-Za-z]+)', raw_lines)
    tangent_at = tangent_pts
    lines = re.findall(r'[A-Za-z]{2}', re.sub(r'\btangent[A-Za-z]+', '', raw_lines))

    # highlight_arc: AB
    ham = re.search(r'\bhighlight_arc:\s*([A-Za-z]{2,})', inner)
    highlight_arc = ham.group(1)[:2] if ham else ""

    # label_angle: {AOB: "2x", ACB: "?"}
    label_angle: Dict[str, str] = {}
    content = _extract_braced(inner, 'label_angle')
    if content:
        for key, val in re.findall(r'([A-Za-z]{3})\s*:\s*"([^"]*)"', content):
            label_angle[key] = val
        for key, val in re.findall(r'([A-Za-z]{3})\s*:\s*([^",}\s]+)', content):
            if key not in label_angle:
                label_angle[key] = val

    # right_angle_at: [T]
    ram = re.search(r'\bright_angle_at:\s*\[([^\]]*)\]', inner)
    right_angle_at = re.findall(r'[A-Za-z]', ram.group(1)) if ram else []

    # label_length: {OP: "r cm", OM: "d cm", PQ: "?"}
    label_length: Dict[str, str] = {}
    content = _extract_braced(inner, 'label_length')
    if content:
        for key, val in re.findall(r'([A-Za-z]{2})\s*:\s*"([^"]*)"', content):
            label_length[key] = val
        for key, val in re.findall(r'([A-Za-z]{2})\s*:\s*([^",}\s]+)', content):
            if key not in label_length:
                label_length[key] = val

    # midpoint: {M: AB, N: CD}
    midpoint: Dict[str, str] = {}
    content = _extract_braced(inner, 'midpoint')
    if content:
        for key, val in re.findall(r'([A-Za-z]+)\s*:\s*([A-Za-z]{2})', content):
            midpoint[key] = val

    return CircleTheoremDiagram(
        radius=radius,
        points=points,
        lines=lines,
        tangent_at=tangent_at,
        highlight_arc=highlight_arc,
        label_angle=label_angle,
        right_angle_at=right_angle_at,
        label_length=label_length,
        midpoint=midpoint,
    )


# ── Viewbox ───────────────────────────────────────────────────────────────────

def viewbox(d: CircleTheoremDiagram):
    # Default viewBox is (-30, -18, 60, 36). 30% taller → height 46.8, min_y -23.4.
    # The auto-zoom preserves this aspect ratio, so the rendered SVG is ~30% taller.
    return (-30, -23.4, 60, 46.8)


# ── Render ────────────────────────────────────────────────────────────────────

def render(d: CircleTheoremDiagram, viz_scale: float = 1.0) -> str:
    R        = 10.0              # SVG circle radius (fixed; viewBox scales around it)
    sw       = 0.10 * viz_scale  # all strokes (circle, chords, radii, tangent)
    fs       = 2.8  * viz_scale  # vertex label size
    fs_a     = 2.0  * viz_scale  # angle label size
    arc_r    = 2.0  * viz_scale  # angle-arc marker radius
    ra_s     = 1.1  * viz_scale  # right-angle marker arm length
    gap      = 2.8  * viz_scale  # vertex label clearance beyond circumference
    dot_r    = 0.38 * viz_scale  # point dot radius
    arc_sw   = 1.26 * viz_scale  # highlight arc stroke width
    lbl_dist = 4.6  * viz_scale  # angle label distance from vertex (arc_r + offset)

    C_MAIN  = "#1a1a2e"
    C_LABEL = "#2563eb"
    C_TAN  = "#dc2626"
    C_ARC  = "#2563eb"
    C_GREY = "#6b7280"

    out = []

    # ── SVG coordinates ───────────────────────────────────────────────────────
    coords: Dict[str, Tuple[float, float]] = {}

    # Pass 1: direct points (centre, circumference angle, explicit coords)
    for name, val in d.points.items():
        if val == 'centre':
            coords[name] = (0.0, 0.0)
        elif isinstance(val, float):
            coords[name] = _pt(R, val)
        elif isinstance(val, tuple) and isinstance(val[0], float):
            coords[name] = val  # explicit (x, y)

    # Pass 2: intersection points (depend on pass-1 coords)
    def _seg_endpoints(spec: str) -> Optional[Tuple[float, float, float, float]]:
        """Endpoints of a segment spec: 'AB' → coords lookup, 'tangentX' → tangent line."""
        if spec.startswith('tangent'):
            pt_name = spec[len('tangent'):]
            if pt_name in coords and isinstance(d.points.get(pt_name), float):
                rad_t = math.radians(d.points[pt_name])
                tx, ty = coords[pt_name]
                tdx, tdy = math.sin(rad_t), math.cos(rad_t)
                tlen = R * 1.5  # long enough for intersection; _line_intersect uses infinite lines
                return (tx - tdx*tlen, ty - tdy*tlen, tx + tdx*tlen, ty + tdy*tlen)
        elif len(spec) >= 2 and spec[0] in coords and spec[1] in coords:
            return (*coords[spec[0]], *coords[spec[1]])
        return None

    for name, val in d.points.items():
        if isinstance(val, tuple) and isinstance(val[0], str):
            e1 = _seg_endpoints(val[0])
            e2 = _seg_endpoints(val[1])
            if e1 and e2:
                pt = _line_intersect(*e1, *e2)
                if pt:
                    coords[name] = pt

    # Derived midpoints
    for name, seg in d.midpoint.items():
        if len(seg) >= 2 and seg[0] in coords and seg[1] in coords:
            x1, y1 = coords[seg[0]]
            x2, y2 = coords[seg[1]]
            coords[name] = ((x1 + x2) / 2, (y1 + y2) / 2)

    # ── Segment list for label collision avoidance ───────────────────────────
    drawable_segs: list = []
    for _s in d.lines:
        if len(_s) >= 2 and _s[0] in coords and _s[1] in coords:
            drawable_segs.append((*coords[_s[0]], *coords[_s[1]]))
    for _tpt in d.tangent_at:
        if _tpt in d.points and isinstance(d.points[_tpt], float):
            _rad_t = math.radians(d.points[_tpt])
            _tx, _ty = coords[_tpt]
            _tdx, _tdy = math.sin(_rad_t), math.cos(_rad_t)
            _tlen = R * 1.5
            drawable_segs.append((_tx - _tdx*_tlen, _ty - _tdy*_tlen,
                                   _tx + _tdx*_tlen, _ty + _tdy*_tlen))
    lbl_threshold = fs * 0.55
    obs_threshold = fs + fs_a   # min center-to-center distance between point and length labels

    # ── Highlight arc (drawn behind circle) ───────────────────────────────────
    if len(d.highlight_arc) == 2:
        p1n, p2n = d.highlight_arc[0], d.highlight_arc[1]
        v1, v2 = d.points.get(p1n), d.points.get(p2n)
        if isinstance(v1, float) and isinstance(v2, float):
            a1, a2 = v1, v2
            if (a2 - a1) % 360 > 180:
                a1, a2 = a2, a1        # ensure CCW minor arc
            x1, y1 = _pt(R, a1)
            x2, y2 = _pt(R, a2)
            out.append(
                f'<path d="M{x1:.3f},{y1:.3f} A{R},{R} 0 0 0 {x2:.3f},{y2:.3f}" '
                f'fill="none" stroke="{C_ARC}" stroke-width="{arc_sw:.3f}" '
                f'stroke-linecap="round" opacity="0.75"/>'
            )

    # ── Circle ────────────────────────────────────────────────────────────────
    out.append(
        f'<circle cx="0" cy="0" r="{R}" fill="none" '
        f'stroke="{C_MAIN}" stroke-width="{sw}"/>'
    )

    # ── Lines (chords / radii / secants) ─────────────────────────────────────
    for seg in d.lines:
        if len(seg) < 2 or seg[0] not in coords or seg[1] not in coords:
            continue
        x1, y1 = coords[seg[0]]
        x2, y2 = coords[seg[1]]
        out.append(
            f'<line x1="{x1:.3f}" y1="{y1:.3f}" x2="{x2:.3f}" y2="{y2:.3f}" '
            f'stroke="{C_TAN}" stroke-width="{sw}" stroke-linecap="round"/>'
        )

    # ── Tangent line ──────────────────────────────────────────────────────────
    for tpt in d.tangent_at:
        if tpt in d.points and isinstance(d.points[tpt], float):
            rad_t = math.radians(d.points[tpt])
            tx, ty = coords[tpt]
            tdx, tdy = math.sin(rad_t), math.cos(rad_t)   # perpendicular to radius
            tlen = R * 1.5
            out.append(
                f'<line '
                f'x1="{tx - tdx*tlen:.3f}" y1="{ty - tdy*tlen:.3f}" '
                f'x2="{tx + tdx*tlen:.3f}" y2="{ty + tdy*tlen:.3f}" '
                f'stroke="{C_TAN}" stroke-width="{sw}" stroke-linecap="round"/>'
            )

    # ── Right-angle markers ───────────────────────────────────────────────────
    for pt_name in d.right_angle_at:
        if pt_name not in coords:
            continue
        vx, vy = coords[pt_name]
        arm1: Optional[Tuple[float, float]] = None
        arm2: Optional[Tuple[float, float]] = None

        if pt_name in d.tangent_at and isinstance(d.points.get(pt_name), float):
            rad_t = math.radians(d.points[pt_name])
            arm1 = (-math.cos(rad_t), math.sin(rad_t))   # toward centre
            arm2 = (math.sin(rad_t), math.cos(rad_t))    # along tangent
        else:
            connected = []
            for seg in d.lines:
                if len(seg) >= 2:
                    other = None
                    if seg[0] == pt_name and seg[1] in coords:
                        other = coords[seg[1]]
                    elif seg[1] == pt_name and seg[0] in coords:
                        other = coords[seg[0]]
                    if other:
                        connected.append((other[0] - vx, other[1] - vy))
            if len(connected) >= 2:
                arm1 = (connected[0][0], connected[0][1])
                arm2 = (connected[1][0], connected[1][1])

        if arm1 and arm2:
            n1, n2 = math.hypot(*arm1), math.hypot(*arm2)
            if n1 > 1e-9 and n2 > 1e-9:
                a1x, a1y = arm1[0] / n1, arm1[1] / n1
                a2x, a2y = arm2[0] / n2, arm2[1] / n2
                p1x, p1y = vx + a1x * ra_s, vy + a1y * ra_s
                p3x, p3y = vx + a2x * ra_s, vy + a2y * ra_s
                p2x, p2y = p1x + a2x * ra_s, p1y + a2y * ra_s
                out.append(
                    f'<polyline points="{p1x:.3f},{p1y:.3f} {p2x:.3f},{p2y:.3f} '
                    f'{p3x:.3f},{p3y:.3f}" '
                    f'fill="none" stroke="{C_GREY}" stroke-width="{sw}"/>'
                )

    # ── Angle arc markers and labels ──────────────────────────────────────────
    for triplet, label in d.label_angle.items():
        if len(triplet) < 3:
            continue
        p_a, p_v, p_b = triplet[0], triplet[1], triplet[2]
        if any(p not in coords for p in (p_a, p_v, p_b)):
            continue
        vx, vy = coords[p_v]

        da = _math_angle(vx, vy, *coords[p_a])
        db = _math_angle(vx, vy, *coords[p_b])

        # Normalise to the minor span going CCW from da to db
        span = (db - da) % 360
        if span > 180:
            da, db = db, da
            span = 360 - span

        # Arc endpoints on circle of radius arc_r centred at vertex
        e1x = vx + arc_r * math.cos(math.radians(da))
        e1y = vy - arc_r * math.sin(math.radians(da))
        e2x = vx + arc_r * math.cos(math.radians(db))
        e2y = vy - arc_r * math.sin(math.radians(db))

        # sweep=0 → CCW in math space (matches our angle convention)
        out.append(
            f'<path d="M{e1x:.3f},{e1y:.3f} '
            f'A{arc_r},{arc_r} 0 0 0 {e2x:.3f},{e2y:.3f}" '
            f'fill="none" stroke="{C_MAIN}" stroke-width="{sw}"/>'
        )

        mid_deg = (da + span / 2) % 360
        lx = vx + lbl_dist * math.cos(math.radians(mid_deg))
        ly = vy - lbl_dist * math.sin(math.radians(mid_deg))
        out.append(_label_svg(lx, ly, label, fs_a, fill=C_LABEL))

    # ── Segment length labels ─────────────────────────────────────────────────
    placed_labels: list = []   # centers of placed length labels; used by point-label avoidance
    lbl_perp = 1.8 * viz_scale  # perpendicular offset from segment midpoint
    for seg, label in d.label_length.items():
        if len(seg) < 2 or seg[0] not in coords or seg[1] not in coords:
            continue
        x1, y1 = coords[seg[0]]
        x2, y2 = coords[seg[1]]
        mx, my = (x1 + x2) / 2, (y1 + y2) / 2
        dx, dy = x2 - x1, y2 - y1
        slen = math.hypot(dx, dy)
        if slen < 1e-9:
            continue
        # Perpendicular direction: 90° CCW rotation of segment direction
        px, py = -dy / slen, dx / slen
        # Flip toward outside the circle (away from centre) for readability
        if px * mx + py * my < 0:
            px, py = -px, -py
        # If a named midpoint sits on this segment, flip label to inside to avoid clash
        if seg in d.midpoint.values():
            px, py = -px, -py
        lx = mx + px * lbl_perp
        ly = my + py * lbl_perp
        other_segs = [s for s in drawable_segs if s != (x1, y1, x2, y2)]
        lx, ly = _clear_label(lx, ly, mx, my, other_segs, lbl_threshold,
                               circle=(0.0, 0.0, R))
        out.append(_label_svg(lx, ly, label, fs_a, fill=C_LABEL))
        placed_labels.append((lx, ly))

    # ── Point dots ────────────────────────────────────────────────────────────
    for name, (x, y) in coords.items():
        out.append(f'<circle cx="{x:.3f}" cy="{y:.3f}" r="{dot_r:.3f}" fill="{C_MAIN}"/>')

    # ── Point labels ──────────────────────────────────────────────────────────
    # Midpoint labels (tracked separately since they're not in d.points)
    for name in d.midpoint:
        if name not in coords:
            continue
        mx, my = coords[name]
        r = math.hypot(mx, my)
        if r > 1e-9:
            lx = mx + gap * mx / r
            ly = my + gap * my / r
        else:
            lx, ly = mx - 1.4, my - 1.6
        lx, ly = _clear_label(lx, ly, mx, my, drawable_segs, lbl_threshold,
                               placed_labels, obs_threshold, circle=(0.0, 0.0, R))
        out.append(_label_svg(lx, ly, name, fs, fill=C_LABEL))

    # All points from d.points
    for name, val in d.points.items():
        if name not in coords:
            continue
        x, y = coords[name]
        if val == 'centre':
            lx, ly = x - 1.4, y - 1.6
        elif isinstance(val, float):
            # Circumference point: offset radially outward at the point's own angle
            rad = math.radians(val)
            lx = x + gap * math.cos(rad)
            ly = y - gap * math.sin(rad)
        else:
            # Explicit coord or intersection: offset radially from circle centre
            r_dist = math.hypot(x, y)
            if r_dist > 1e-9:
                lx = x + gap * x / r_dist
                ly = y + gap * y / r_dist
            else:
                lx, ly = x - 1.4, y - 1.6
        lx, ly = _clear_label(lx, ly, x, y, drawable_segs, lbl_threshold,
                               placed_labels, obs_threshold, circle=(0.0, 0.0, R))
        out.append(_label_svg(lx, ly, name, fs, fill=C_LABEL))

    return "\n".join(out)
