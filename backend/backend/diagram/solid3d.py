import re
import math
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

DIAGRAM_TYPE = "Solid3D"
SUPPORTS_VIZ_SCALE = True

# ── Oblique projection ────────────────────────────────────────────────────────
# Matches CompositeSolid: (x, y, z) → screen (sx, sy), y is up, z recedes right
_OX = 0.35
_OY = -0.35

# SVG style constants
_C_WIRE        = "#1e293b"   # wireframe solid edges
_C_WIRE_HIDDEN = "#cbd5e1"   # wireframe hidden/dashed edges
_C_ANN_SOLID   = "#1e293b"   # annotation labels, arcs, markers
_C_ANN_LINE    = "#dc2626"   # annotation solid lines (lines: parameter)
_C_ANN_DASH    = "#64748b"   # annotation dashed lines
_C_HIGHLIGHT   = "#2563eb"   # highlight lines
_C_RA          = "#1e293b"   # right-angle markers

_FS_POINT  = 1.5   # point label font-size in SVG user units
_FS_LEN    = 1.25  # length label font-size in SVG user units
_FS_ANGLE  = 1.25  # angle label font-size in SVG user units


# ── Dataclass ─────────────────────────────────────────────────────────────────

@dataclass
class Solid3DDiagram:
    shape:          str                         = "rect_prism"
    w:              float                       = 4.0
    h:              float                       = 3.0
    d:              float                       = 5.0
    points:         Dict[str, object]           = field(default_factory=dict)
    lines:          List[str]                   = field(default_factory=list)
    dash:           List[str]                   = field(default_factory=list)
    highlight:      List[Tuple[str, str]]        = field(default_factory=list)
    right_angle_at: Dict[str, List[str]]        = field(default_factory=dict)
    label_angle:    Dict[str, str]               = field(default_factory=dict)
    label_length:   Dict[str, str]              = field(default_factory=dict)
    label_point:    Dict[str, str]              = field(default_factory=dict)


# ── Parser ────────────────────────────────────────────────────────────────────

def _extract_braced(text: str, key: str) -> Optional[str]:
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


def _extract_bracketed(text: str, key: str) -> Optional[str]:
    m = re.search(rf'\b{re.escape(key)}\s*:\s*\[', text)
    if not m:
        return None
    start = m.end() - 1
    depth = 0
    for i in range(start, len(text)):
        if text[i] == '[':
            depth += 1
        elif text[i] == ']':
            depth -= 1
            if depth == 0:
                return text[start + 1:i]
    return None


def _parse_points(raw: str) -> Dict[str, object]:
    """Parse points dict: {A: (0,0,0), M: midpoint(AB), O: centre_base, ...}"""
    pts = {}
    # Split on comma-separated entries at top level
    # Each entry is: NAME: VALUE where VALUE might have parens/nesting
    pattern = re.compile(
        r'(\w+)\s*:\s*'
        r'('
        r'midpoint\s*\(\s*\w+\s*\)'
        r'|foot\s*\([^)]+\)'
        r'|centre_base|centre_top'
        r'|\(\s*[\d.,\s]+\)'
        r')'
    )
    for m in pattern.finditer(raw):
        name = m.group(1)
        val  = m.group(2).strip()
        if val.startswith('('):
            nums = re.findall(r'[\d.]+', val)
            if len(nums) == 3:
                pts[name] = tuple(float(n) for n in nums)
        else:
            pts[name] = val   # deferred: 'midpoint(AB)', 'foot(G,base)', etc.
    return pts


def _parse_seg_list(raw: str) -> List[str]:
    """Parse a bracketed list like [AG, CG, BF]."""
    return [s.strip() for s in raw.split(',') if s.strip()]


def _parse_highlight_list(raw: str) -> List[Tuple[str, str]]:
    """Parse highlight list supporting both [AC, AF] and [(AC, blue), (AF, red)]."""
    # Split on top-level commas only (ignore commas inside parentheses)
    tokens: List[str] = []
    depth, buf = 0, []
    for ch in raw:
        if ch == '(':
            depth += 1; buf.append(ch)
        elif ch == ')':
            depth -= 1; buf.append(ch)
        elif ch == ',' and depth == 0:
            tokens.append(''.join(buf).strip()); buf = []
        else:
            buf.append(ch)
    if buf:
        tokens.append(''.join(buf).strip())

    result = []
    for token in tokens:
        token = token.strip()
        if not token:
            continue
        if token.startswith('(') and token.endswith(')'):
            parts = [p.strip() for p in token[1:-1].split(',', 1)]
            seg = parts[0]
            color = parts[1] if len(parts) == 2 else _C_HIGHLIGHT
            result.append((seg, color))
        else:
            result.append((token, _C_HIGHLIGHT))
    return result


def _parse_right_angle_at(text: str) -> Dict[str, List[str]]:
    raw = _extract_braced(text, 'right_angle_at')
    if not raw:
        return {}
    result = {}
    for m in re.finditer(r'(\w)\s*:\s*\[([^\]]*)\]', raw):
        pt = m.group(1)
        segs = [s.strip() for s in m.group(2).split(',') if s.strip()]
        result[pt] = segs
    return result


def _parse_label_length(text: str) -> Dict[str, str]:
    raw = _extract_braced(text, 'label_length')
    if not raw:
        return {}
    result = {}
    # Explicit values: AD: "5 cm"
    for m in re.finditer(r'(\w+)\s*:\s*"([^"]*)"', raw):
        result[m.group(1)] = m.group(2)
    # Bare names (no colon): AD, AB, BF — value computed at render time
    remaining = re.sub(r'\w+\s*:\s*"[^"]*"', '', raw)
    for m in re.finditer(r'\b([A-Za-z]\w*)\b', remaining):
        name = m.group(1)
        if name not in result:
            result[name] = ''
    return result


def _parse_label_point(text: str) -> Dict[str, str]:
    raw = _extract_braced(text, 'label_point')
    if not raw:
        return {}
    result = {}
    for m in re.finditer(r'(\w+)\s*:\s*"([^"]*)"', raw):
        result[m.group(1)] = m.group(2)
    remaining = re.sub(r'\w+\s*:\s*"[^"]*"', '', raw)
    for m in re.finditer(r'\b([A-Za-z]\w*)\b', remaining):
        name = m.group(1)
        if name not in result:
            result[name] = name
    return result


def parse(line: str) -> Optional[Solid3DDiagram]:
    m = re.match(r'Solid3D\s*\((.+)\)\s*$', line.strip(), re.DOTALL)
    if not m:
        return None
    inner = m.group(1)

    def get_str(key, default=""):
        mm = re.search(rf'\b{key}\s*:\s*(\w+)', inner)
        return mm.group(1) if mm else default

    def get_num(key, default=0.0):
        mm = re.search(rf'\b{key}\s*:\s*([\d.]+)', inner)
        return float(mm.group(1)) if mm else default

    shape = get_str('shape', 'rect_prism')
    w = get_num('w', 4.0)
    h = get_num('h', 3.0)
    d = get_num('d', 5.0)

    pts_raw = _extract_braced(inner, 'points')
    points = _parse_points(pts_raw) if pts_raw else {}

    lines_raw = _extract_bracketed(inner, 'lines')
    lines = _parse_seg_list(lines_raw) if lines_raw else []

    dash_raw = _extract_bracketed(inner, 'dash')
    dash = _parse_seg_list(dash_raw) if dash_raw else []

    hl_raw = _extract_bracketed(inner, 'highlight')
    highlight = _parse_highlight_list(hl_raw) if hl_raw else []

    right_angle_at = _parse_right_angle_at(inner)

    label_angle: Dict[str, str] = {}
    la_content = _extract_braced(inner, 'label_angle')
    if la_content:
        for _key, _val in re.findall(r'([A-Za-z]{3})\s*:\s*"([^"]*)"', la_content):
            label_angle[_key] = _val
        for _key, _val in re.findall(r'([A-Za-z]{3})\s*:\s*([^",}\s]+)', la_content):
            if _key not in label_angle:
                label_angle[_key] = _val

    label_length   = _parse_label_length(inner)
    label_point    = _parse_label_point(inner)

    return Solid3DDiagram(
        shape=shape, w=w, h=h, d=d,
        points=points,
        lines=lines, dash=dash, highlight=highlight,
        right_angle_at=right_angle_at,
        label_angle=label_angle,
        label_length=label_length,
        label_point=label_point,
    )


# ── Projection ────────────────────────────────────────────────────────────────

def _proj(ux: float, uy: float, uz: float,
          w: float, h: float, d: float,
          scale: float) -> Tuple[float, float]:
    """Unit-cube coords → SVG screen coords (origin at shape's visual centre)."""
    sx = (ux * w + uz * d * _OX) * scale
    sy = (-uy * h + uz * d * _OY) * scale
    return sx, sy


# ── Shape wireframe edge tables ───────────────────────────────────────────────

# Unit-cube vertices
_RECT_PRISM_VERTS = {
    'A': (0,0,0), 'B': (1,0,0), 'C': (1,0,1), 'D': (0,0,1),  # bottom face (y=0)
    'E': (0,1,0), 'F': (1,1,0), 'G': (1,1,1), 'H': (0,1,1),  # top face    (y=1)
}
# (v1, v2, hidden?)
_RECT_PRISM_EDGES = [
    # Bottom face
    ('A','B', False), ('B','C', False), ('C','D', True), ('D','A', True),
    # Top face
    ('E','F', False), ('F','G', False), ('G','H', False), ('H','E', False),
    # Vertical edges
    ('A','E', False), ('B','F', False), ('C','G', False), ('D','H', True),
]

_SQUARE_PYR_VERTS = {
    'A': (0,0,0), 'B': (1,0,0), 'C': (1,0,1), 'D': (0,0,1),
    'P': (0.5, 1, 0.5),
}
_SQUARE_PYR_EDGES = [
    ('A','B', False), ('B','C', False), ('C','D', True), ('D','A', True),
    ('P','A', False), ('P','B', False), ('P','C', False), ('P','D', True),
]

_TRI_PRISM_VERTS = {
    'A': (0,0,0), 'B': (1,0,0), 'C': (0.5,1,0),
    'D': (0,0,1), 'E': (1,0,1), 'F': (0.5,1,1),
}
_TRI_PRISM_EDGES = [
    ('A','B', False), ('B','C', False), ('C','A', False),
    ('D','E', True),  ('E','F', False), ('F','D', True),
    ('A','D', True),  ('B','E', False), ('C','F', False),
]

_SHAPE_VERTS = {
    'rect_prism':      _RECT_PRISM_VERTS,
    'square_pyramid':  _SQUARE_PYR_VERTS,
    'triangular_prism': _TRI_PRISM_VERTS,
}
_SHAPE_EDGES = {
    'rect_prism':      _RECT_PRISM_EDGES,
    'square_pyramid':  _SQUARE_PYR_EDGES,
    'triangular_prism': _TRI_PRISM_EDGES,
}


# ── Point resolution ──────────────────────────────────────────────────────────

def _resolve_points(
    raw_points: Dict[str, object],
    seed_verts: Optional[Dict[str, Tuple[float, float, float]]] = None,
) -> Dict[str, Tuple[float, float, float]]:
    """Resolve all named points to unit-cube (ux, uy, uz) tuples.

    seed_verts: shape vertices used as reference for midpoint/foot lookups
    but not included in the returned dict.
    """
    resolved: Dict[str, Tuple[float, float, float]] = {}

    # First pass: literal coordinates
    for name, val in raw_points.items():
        if isinstance(val, tuple):
            resolved[name] = val
        elif val == 'centre_base':
            resolved[name] = (0.5, 0.0, 0.5)
        elif val == 'centre_top':
            resolved[name] = (0.5, 1.0, 0.5)

    # Combined lookup: shape vertices + already-resolved user points
    lookup: Dict[str, Tuple[float, float, float]] = {}
    if seed_verts:
        lookup.update(seed_verts)
    lookup.update(resolved)

    # Second pass: deferred (midpoint, foot)
    for name, val in raw_points.items():
        if name in resolved:
            continue
        if not isinstance(val, str):
            continue
        m = re.match(r'midpoint\s*\(\s*(\w)(\w)\s*\)', val)
        if m:
            a, b = m.group(1), m.group(2)
            if a in lookup and b in lookup:
                pa, pb = lookup[a], lookup[b]
                resolved[name] = (
                    (pa[0]+pb[0])/2, (pa[1]+pb[1])/2, (pa[2]+pb[2])/2
                )
                lookup[name] = resolved[name]
            continue
        m = re.match(r'foot\s*\(\s*(\w)\s*,\s*base\s*\)', val)
        if m:
            pt_name = m.group(1)
            if pt_name in lookup:
                ux, uy, uz = lookup[pt_name]
                resolved[name] = (ux, 0.0, uz)
                lookup[name] = resolved[name]
            continue

    return resolved


# ── SVG helpers ───────────────────────────────────────────────────────────────

def _line_svg(x1, y1, x2, y2, color, sw, dash_array="") -> str:
    da = f' stroke-dasharray="{dash_array}"' if dash_array else ''
    return (f'<line x1="{x1:.3f}" y1="{y1:.3f}" x2="{x2:.3f}" y2="{y2:.3f}"'
            f' stroke="{color}" stroke-width="{sw:.3f}" stroke-linecap="round"{da}/>')


def _text_svg(x, y, text, fs, color, weight="normal", anchor="middle") -> str:
    return (f'<text x="{x:.3f}" y="{y:.3f}" font-size="{fs:.3f}"'
            f' font-family="system-ui,-apple-system,sans-serif"'
            f' fill="{color}" font-weight="{weight}"'
            f' text-anchor="{anchor}" dominant-baseline="middle">{text}</text>')


def _dot_svg(x, y, r, color) -> str:
    return f'<circle cx="{x:.3f}" cy="{y:.3f}" r="{r:.3f}" fill="{color}"/>'


# ── Right-angle marker ────────────────────────────────────────────────────────

def _right_angle_svg(vx, vy, ax, ay, bx, by, size: float, sw: float) -> str:
    """Draw a small square at (vx,vy) between rays toward (ax,ay) and (bx,by)."""
    def unit(dx, dy):
        d = math.hypot(dx, dy)
        if d < 1e-12:
            return 0.0, 0.0
        return dx/d, dy/d

    ux, uy = unit(ax - vx, ay - vy)
    wx, wy = unit(bx - vx, by - vy)
    # Four corners of the square
    p1x = vx + ux * size
    p1y = vy + uy * size
    p2x = vx + ux * size + wx * size
    p2y = vy + uy * size + wy * size
    p3x = vx + wx * size
    p3y = vy + wy * size
    pts = f"{p1x:.3f},{p1y:.3f} {p2x:.3f},{p2y:.3f} {p3x:.3f},{p3y:.3f}"
    return (f'<polyline points="{pts}" fill="none"'
            f' stroke="{_C_RA}" stroke-width="{sw:.3f}" stroke-linejoin="miter"/>')


# ── Angle arc ─────────────────────────────────────────────────────────────────

def _angle_arc_svg(vx, vy, ax, ay, bx, by,
                   label: str, radius: float, sw: float, fs: float,
                   color: str = _C_ANN_SOLID) -> str:
    """Curved arc + label between two rays from vertex V."""
    def angle_to(px, py):
        return math.atan2(py - vy, px - vx)

    a1 = angle_to(ax, ay)
    a2 = angle_to(bx, by)
    # Always draw the shorter arc (< π)
    diff = (a2 - a1 + math.pi) % (2 * math.pi) - math.pi
    if abs(diff) < 1e-6:
        return ''

    # Ensure we go from a1 to a2 via the short route
    start = a1
    end   = a1 + diff
    large_arc = 0  # always short arc

    sx = vx + radius * math.cos(start)
    sy = vy + radius * math.sin(start)
    ex = vx + radius * math.cos(end)
    ey = vy + radius * math.sin(end)
    sweep = 1 if diff > 0 else 0

    path = (f'<path d="M {sx:.3f} {sy:.3f} A {radius:.3f} {radius:.3f} 0'
            f' {large_arc} {sweep} {ex:.3f} {ey:.3f}"'
            f' fill="none" stroke="{color}" stroke-width="{sw:.3f}"/>')

    if label:
        mid_angle = (start + end) / 2
        lx = vx + (radius + fs * 1.1) * math.cos(mid_angle)
        ly = vy + (radius + fs * 1.1) * math.sin(mid_angle)
        path += _text_svg(lx, ly, label, fs, color)

    return path


# ── Label collision avoidance ────────────────────────────────────────────────

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
                 shape_centroid: Optional[Tuple[float, float]] = None) -> Tuple[float, float]:
    """
    Return a label position clear of line segments and placed-label obstacles,
    preferring positions outside the shape (away from shape_centroid).
    Rotates the offset vector in 30° steps; returns the candidate with the best score.
    """
    def _score(cx: float, cy: float) -> float:
        seg_score = min((_pt_seg_dist(cx, cy, *s) for s in segs), default=math.inf) / threshold
        if obstacles and obs_threshold > 0:
            obs_score = min((math.hypot(cx - ox, cy - oy)
                             for ox, oy in obstacles), default=math.inf) / obs_threshold
            seg_score = min(seg_score, obs_score)
        if shape_centroid is not None:
            # Penalise positions on the opposite side of the centroid from the anchor
            scx, scy = shape_centroid
            if (ax - scx) * (cx - scx) + (ay - scy) * (cy - scy) < 0:
                seg_score *= 0.2
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


# ── Auto length computation ───────────────────────────────────────────────────

def _auto_length(a: str, b: str, pts: Dict[str, Tuple[float, float, float]],
                 w: float, h: float, d: float) -> str:
    if a not in pts or b not in pts:
        return ''
    ux1, uy1, uz1 = pts[a]
    ux2, uy2, uz2 = pts[b]
    length = math.sqrt(((ux2-ux1)*w)**2 + ((uy2-uy1)*h)**2 + ((uz2-uz1)*d)**2)
    if abs(length - round(length)) < 1e-9:
        return str(int(round(length)))
    return f"{length:.2f}"


# ── Main render ───────────────────────────────────────────────────────────────

def render(d: Solid3DDiagram, viz_scale: float = 1.0) -> str:
    w, h, depth = d.w, d.h, d.d

    # Scale: fit shape roughly in a ~20-unit window (SVG coords)
    longest = max(w, h, depth, 1.0)
    scale = 14.0 / longest * viz_scale

    sw_wire = 0.125 * viz_scale
    sw_ann  = 0.15  * viz_scale

    sw_ra   = 0.125 * viz_scale
    sw_arc  = 0.11  * viz_scale
    ra_size = 1.0  * viz_scale
    arc_r   = 1.5  * viz_scale
    lbl_off = 1.5  * viz_scale   # length label perp offset (extra room for fixed-px font)

    def proj(ux, uy, uz):
        return _proj(ux, uy, uz, w, h, depth, scale)

    # ── Wireframe ──────────────────────────────────────────────────────────────
    shape_verts = _SHAPE_VERTS.get(d.shape, _RECT_PRISM_VERTS)
    shape_edges = _SHAPE_EDGES.get(d.shape, _RECT_PRISM_EDGES)

    out = []

    for v1, v2, hidden in shape_edges:
        if hidden and v1 in shape_verts and v2 in shape_verts:
            sx1, sy1 = proj(*shape_verts[v1])
            sx2, sy2 = proj(*shape_verts[v2])
            out.append(_line_svg(sx1, sy1, sx2, sy2, _C_WIRE_HIDDEN, sw_wire))

    # ── Resolve named points ───────────────────────────────────────────────────
    coords = _resolve_points(d.points, seed_verts=shape_verts)
    all_pts_3d = dict(shape_verts)
    all_pts_3d.update(coords)

    def pt(name) -> Optional[Tuple[float, float]]:
        if name not in all_pts_3d:
            return None
        ux, uy, uz = all_pts_3d[name]
        return proj(ux, uy, uz)

    # ── Annotation lines: dashed ───────────────────────────────────────────────
    for seg in d.dash:
        if len(seg) < 2:
            continue
        a, b = seg[0], seg[1]
        pa, pb = pt(a), pt(b)
        if pa and pb:
            out.append(_line_svg(pa[0], pa[1], pb[0], pb[1],
                                 _C_ANN_DASH, sw_ann, "2.5 2"))

    # ── Annotation lines: solid ───────────────────────────────────────────────
    for seg in d.lines:
        if len(seg) < 2:
            continue
        a, b = seg[0], seg[1]
        pa, pb = pt(a), pt(b)
        if pa and pb:
            out.append(_line_svg(pa[0], pa[1], pb[0], pb[1],
                                 _C_ANN_LINE, sw_ann))

    # ── Highlight lines ────────────────────────────────────────────────────────
    for seg, color in d.highlight:
        if len(seg) < 2:
            continue
        a, b = seg[0], seg[1]
        pa, pb = pt(a), pt(b)
        if pa and pb:
            out.append(_line_svg(pa[0], pa[1], pb[0], pb[1], color, sw_ann))

    for v1, v2, hidden in shape_edges:
        if not hidden and v1 in shape_verts and v2 in shape_verts:
            sx1, sy1 = proj(*shape_verts[v1])
            sx2, sy2 = proj(*shape_verts[v2])
            out.append(_line_svg(sx1, sy1, sx2, sy2, _C_WIRE, sw_wire))

    # Only render annotations on pass 2 (viz_scale != 1.0)
    if viz_scale == 1.0:
        return "\n".join(out)

    # ── Collect 2D segments for label collision avoidance ─────────────────────
    all_segs_2d = []
    for _v1, _v2, _ in shape_edges:
        if _v1 in shape_verts and _v2 in shape_verts:
            _p1 = proj(*shape_verts[_v1])
            _p2 = proj(*shape_verts[_v2])
            all_segs_2d.append((*_p1, *_p2))
    for _seg in (*d.dash, *d.lines, *(seg for seg, _ in d.highlight)):
        if len(_seg) >= 2:
            _pa, _pb = pt(_seg[0]), pt(_seg[1])
            if _pa and _pb:
                all_segs_2d.append((*_pa, *_pb))
    lbl_threshold = _FS_LEN  * viz_scale * 0.55
    obs_threshold = (_FS_LEN + _FS_POINT) * viz_scale
    placed_labels: list = []
    shape_centroid = proj(0.5, 0.5, 0.5)

    # ── Right-angle markers ────────────────────────────────────────────────────
    for vertex, segs in d.right_angle_at.items():
        if len(segs) < 2:
            continue
        pv = pt(vertex)
        if not pv:
            continue
        seg1, seg2 = segs[0], segs[1]
        # Each seg is like "AC" — find the other endpoint from vertex
        def other_end(seg_name, v_name):
            if len(seg_name) < 2:
                return None
            a, b = seg_name[0], seg_name[1]
            other = b if a == v_name else (a if b == v_name else None)
            return other

        o1 = other_end(seg1, vertex)
        o2 = other_end(seg2, vertex)
        if o1 and o2:
            p1 = pt(o1)
            p2 = pt(o2)
            if p1 and p2:
                out.append(_right_angle_svg(
                    pv[0], pv[1], p1[0], p1[1], p2[0], p2[1],
                    ra_size, sw_ra
                ))

    # ── Angle arc labels ───────────────────────────────────────────────────────
    for triplet, label in d.label_angle.items():
        if len(triplet) < 3:
            continue
        p_a, p_v, p_b = triplet[0], triplet[1], triplet[2]
        pv = pt(p_v)
        pa = pt(p_a)
        pb = pt(p_b)
        if pv and pa and pb:
            out.append(_angle_arc_svg(
                pv[0], pv[1], pa[0], pa[1], pb[0], pb[1],
                label, arc_r, sw_arc, _FS_ANGLE * viz_scale,
                color=_C_ANN_LINE
            ))

    # ── Length labels ──────────────────────────────────────────────────────────
    for seg, label in d.label_length.items():
        if len(seg) < 2:
            continue
        a, b = seg[0], seg[1]
        if not label:
            label = _auto_length(a, b, all_pts_3d, w, h, depth)
        pa, pb = pt(a), pt(b)
        if not (pa and pb and label):
            continue
        mx, my = (pa[0]+pb[0])/2, (pa[1]+pb[1])/2
        sdx, sdy = pb[0]-pa[0], pb[1]-pa[1]
        slen = math.hypot(sdx, sdy)
        if slen < 1e-9:
            continue
        perp_x, perp_y = -sdy/slen, sdx/slen
        # Flip to point away from the shape centroid
        scx, scy = shape_centroid
        if perp_x * (mx - scx) + perp_y * (my - scy) < 0:
            perp_x, perp_y = -perp_x, -perp_y
        lx = mx + perp_x * lbl_off
        ly = my + perp_y * lbl_off
        other_segs = [s for s in all_segs_2d
                      if s != (pa[0], pa[1], pb[0], pb[1])]
        lx, ly = _clear_label(lx, ly, mx, my, other_segs, lbl_threshold,
                               placed_labels, obs_threshold, shape_centroid)
        col = _C_ANN_DASH if seg in d.dash else (_C_ANN_LINE if seg in d.lines else _C_ANN_SOLID)
        out.append(_text_svg(lx, ly, label, _FS_LEN * viz_scale, col))
        placed_labels.append((lx, ly))

    # ── Point labels ──────────────────────────────────────────────────────────
    scx, scy = shape_centroid

    for pt_name, label_text in d.label_point.items():
        p = pt(pt_name)
        if not p:
            continue
        px, py = p
        dx, dy = px - scx, py - scy
        dist = math.hypot(dx, dy)
        if dist < 1e-6:
            dx, dy = 0.0, -1.0
        else:
            dx, dy = dx/dist, dy/dist
        off = _FS_POINT * viz_scale * 1.4
        lx, ly = px + dx * off, py + dy * off
        lx, ly = _clear_label(lx, ly, px, py, all_segs_2d, lbl_threshold,
                               placed_labels, obs_threshold, shape_centroid)
        out.append(_dot_svg(px, py, 0.1, _C_ANN_SOLID))
        out.append(_text_svg(lx, ly, label_text, _FS_POINT * viz_scale, _C_ANN_SOLID, "bold"))
        placed_labels.append((lx, ly))

    return "\n".join(out)
