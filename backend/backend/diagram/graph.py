import re
import math
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

DIAGRAM_TYPE = "Graph"
SUPPORTS_VIZ_SCALE = True

_FONT    = "system-ui, -apple-system, sans-serif"
_C_V     = "#2563eb"   # vertex fill
_C_V_HL  = "#dc2626"   # highlighted vertex
_C_E     = "#334155"   # edge stroke
_C_E_HL  = "#dc2626"   # highlighted edge
_C_FACE  = "#dbeafe"   # bounded-face fill
_C_FACE_S= "#93c5fd"   # face polygon stroke
_C_LAB   = "#ffffff"   # vertex label (on fill)
_C_DEG   = "#64748b"   # degree text
_C_WT    = "#374151"   # edge-weight text
_C_FN    = "#1d4ed8"   # face-number text

_VB  = 60.0            # viewBox side length
_PAD = 7.0             # padding inside viewBox
_SC  = (_VB - 2 * _PAD) / 10.0   # SVG units per user unit (4.6)


@dataclass
class GraphDiagram:
    vertices:           Dict[str, Tuple[float, float]]
    edges:              List[Tuple[str, str]]
    loops:              List[str]
    directed:           bool
    highlight_vertices: List[str]
    highlight_edges:    List[Tuple[str, str]]
    label_degrees:      bool
    show_faces:         bool
    label_edge_weights: Dict[str, str]


# ── Coordinate helpers ────────────────────────────────────────────────────────

def _sv(ux: float, uy: float) -> Tuple[float, float]:
    return _PAD + ux * _SC, _PAD + uy * _SC


def _shorten(x1: float, y1: float, x2: float, y2: float, r: float) -> Tuple[float, float]:
    """Return point r units from (x2,y2) toward (x1,y1)."""
    dx, dy = x1 - x2, y1 - y2
    d = math.hypot(dx, dy)
    if d < 1e-9:
        return x2, y2
    return x2 + r * dx / d, y2 + r * dy / d


# ── Parsing ───────────────────────────────────────────────────────────────────

def _extract_region(text: str, key: str) -> str:
    """Extract raw value text for 'key:' from a flat parameter string."""
    m = re.search(rf'(?:^|,)\s*{re.escape(key)}\s*:\s*', text)
    if not m:
        return ''
    pos   = m.end()
    depth = 0
    in_q  = False
    qc    = ''
    while pos < len(text):
        ch = text[pos]
        if in_q:
            if ch == qc:
                in_q = False
        elif ch in ('"', "'"):
            in_q = True
            qc   = ch
        elif ch in '([{':
            depth += 1
        elif ch in ')]}':
            if depth > 0:
                depth -= 1
            else:
                break
        elif depth == 0 and ch == ',':
            if re.match(r',\s*\w+\s*:', text[pos:]):
                break
        pos += 1
    return text[m.end():pos].strip()


def _parse_vertices(text: str) -> Dict[str, Tuple[float, float]]:
    out: Dict[str, Tuple[float, float]] = {}
    for m in re.finditer(
        r'(\w+)\s*:\s*[\(\[]\s*(-?[\d.]+)\s*,\s*(-?[\d.]+)\s*[\)\]]', text
    ):
        out[m.group(1)] = (float(m.group(2)), float(m.group(3)))
    return out


def _parse_edge_list(text: str, known_vertices=None) -> List[Tuple[str, str]]:
    # Bracket format: [A,B] or (A,B)
    bracket = [(m.group(1), m.group(2))
               for m in re.finditer(r'[\[\(]\s*(\w+)\s*,\s*(\w+)\s*[\]\)]', text)]
    if bracket:
        return bracket

    # Shorthand format: "AB, BC, CD" or [AB, BC, CD] or "A-B, B-C" or "A B, B C"
    stripped = text.strip().strip('"\'')
    # Strip outer list brackets: [AB, BC, CD] -> AB, BC, CD
    if stripped.startswith(('[', '(')) and stripped.endswith((']', ')')):
        stripped = stripped[1:-1]
    if not stripped:
        return []

    result: List[Tuple[str, str]] = []
    vset = set(known_vertices) if known_vertices else set()

    for token in (t.strip() for t in stripped.split(',') if t.strip()):
        # Dash-separated: A-B
        if '-' in token:
            parts = [p.strip() for p in token.split('-', 1)]
            if len(parts) == 2 and parts[0] and parts[1]:
                result.append((parts[0], parts[1]))
            continue
        # Space-separated: A B
        parts = token.split()
        if len(parts) == 2:
            result.append((parts[0], parts[1]))
            continue
        # Concatenated: AB -> (A, B) using known vertex names longest-match first
        if len(token) >= 2:
            matched = False
            for vname in sorted(vset, key=len, reverse=True):
                rest = token[len(vname):]
                if token.startswith(vname) and rest in vset:
                    result.append((vname, rest))
                    matched = True
                    break
            if not matched and len(token) == 2:
                result.append((token[0], token[1]))

    return result


def _parse_name_list(text: str) -> List[str]:
    return [s for s in re.split(r'[\s,\[\]{}]+', text.strip()) if re.match(r'^\w+$', s)]


def _parse_weight_dict(text: str) -> Dict[str, str]:
    out: Dict[str, str] = {}
    for m in re.finditer(
        r'(\w+)\s*:\s*(?:"([^"]*)"|\'([^\']*)\'|([^\s,}\]]+))',
        text.strip().strip('{}'),
    ):
        out[m.group(1)] = m.group(2) or m.group(3) or m.group(4) or ''
    return out


def parse(line: str) -> Optional[GraphDiagram]:
    m = re.match(r'Graph\s*\((.+)\)\s*$', line.strip(), re.DOTALL)
    if not m:
        return None
    inner = m.group(1)

    verts_raw = _extract_region(inner, 'vertices')
    vertices  = _parse_vertices(verts_raw)
    if not vertices:
        return None

    vnames = set(vertices.keys())
    return GraphDiagram(
        vertices           = vertices,
        edges              = _parse_edge_list(_extract_region(inner, 'edges'), vnames),
        loops              = _parse_name_list(_extract_region(inner, 'loops')),
        directed           = _extract_region(inner, 'directed').strip().lower() == 'true',
        highlight_vertices = _parse_name_list(_extract_region(inner, 'highlight_vertices')),
        highlight_edges    = _parse_edge_list(_extract_region(inner, 'highlight_edges'), vnames),
        label_degrees      = _extract_region(inner, 'label_degrees').strip().lower() == 'true',
        show_faces         = _extract_region(inner, 'show_faces').strip().lower() == 'true',
        label_edge_weights = _parse_weight_dict(_extract_region(inner, 'label_edge_weights')),
    )


# ── Face detection (half-edge traversal) ──────────────────────────────────────

def _compute_faces(
    vertices: Dict[str, Tuple[float, float]],
    edges: List[Tuple[str, str]],
) -> Tuple[List[List[str]], Optional[List[str]]]:
    """Return (bounded_faces, outer_face) for the planar embedding."""
    adj: Dict[str, List[str]] = {v: [] for v in vertices}
    for u, v in edges:
        if u not in adj or v not in adj or u == v:
            continue
        if v not in adj[u]:
            adj[u].append(v)
        if u not in adj[v]:
            adj[v].append(u)

    def angle(center: str, nbr: str) -> float:
        cx, cy = vertices[center]
        nx, ny = vertices[nbr]
        return math.atan2(ny - cy, nx - cx)

    for v in adj:
        adj[v].sort(key=lambda n: angle(v, n))

    def next_he(u: str, v: str) -> Tuple[Optional[str], Optional[str]]:
        nbrs = adj[v]
        if not nbrs:
            return None, None
        idx = nbrs.index(u)
        return v, nbrs[(idx - 1) % len(nbrs)]

    visited: set = set()
    all_faces: List[List[str]] = []
    max_iters = max(len(edges) * 4 + 10, 100)

    for start_u in sorted(adj):
        for start_v in adj[start_u]:
            if (start_u, start_v) in visited:
                continue
            face: List[str] = []
            cu, cv = start_u, start_v
            iters  = 0
            while (cu, cv) not in visited and iters < max_iters:
                visited.add((cu, cv))
                face.append(cu)
                cu, cv = next_he(cu, cv)
                if cu is None:
                    break
                iters += 1
            if len(face) >= 3:
                all_faces.append(face)

    if not all_faces:
        return [], None

    def signed_area(face: List[str]) -> float:
        pts = [vertices[v] for v in face]
        n   = len(pts)
        return sum(
            pts[i][0] * pts[(i + 1) % n][1] - pts[(i + 1) % n][0] * pts[i][1]
            for i in range(n)
        ) / 2

    areas     = [signed_area(f) for f in all_faces]
    # Outer face is traversed CCW on screen (y-down), giving the most negative signed area.
    outer_idx = min(range(len(all_faces)), key=lambda i: areas[i])
    bounded   = [f for i, f in enumerate(all_faces) if i != outer_idx]
    return bounded, all_faces[outer_idx]


# ── Engine interface ──────────────────────────────────────────────────────────

def viewbox(d: GraphDiagram) -> tuple:
    return (0.0, 0.0, _VB, _VB)


def render(d: GraphDiagram, viz_scale: float = 1.0) -> str:
    out: List[str] = []

    vr  = 3.0 * viz_scale   # vertex radius
    sw  = 0.5 * viz_scale   # stroke width
    fs  = 2.5 * viz_scale   # vertex label font size
    fs2 = 1.9 * viz_scale   # degree / weight font size
    aw  = 3.5 * viz_scale   # arrowhead size

    # ── Arrow markers ─────────────────────────────────────────────────────────
    if d.directed:
        h = aw * 0.7
        def _mkr(mid: str, col: str) -> str:
            return (
                f'<marker id="{mid}" markerWidth="{aw:.3f}" markerHeight="{h:.3f}" '
                f'refX="{aw:.3f}" refY="{h/2:.3f}" orient="auto" '
                f'markerUnits="userSpaceOnUse">'
                f'<polygon points="0 0,{aw:.3f} {h/2:.3f},0 {h:.3f}" fill="{col}"/>'
                f'</marker>'
            )
        out.append(f'<defs>{_mkr("g-arrow", _C_E)}{_mkr("g-arrow-hl", _C_E_HL)}</defs>')

    # ── Faces ─────────────────────────────────────────────────────────────────
    if d.show_faces:
        bounded, outer = _compute_faces(d.vertices, d.edges)
        for fi, face in enumerate(bounded, start=1):
            pts = ' '.join(
                f'{_sv(*d.vertices[v])[0]:.3f},{_sv(*d.vertices[v])[1]:.3f}'
                for v in face
            )
            svxs = [_sv(*d.vertices[v])[0] for v in face]
            svys = [_sv(*d.vertices[v])[1] for v in face]
            fcx  = sum(svxs) / len(svxs)
            fcy  = sum(svys) / len(svys)
            out.append(
                f'<polygon points="{pts}" fill="{_C_FACE}" '
                f'stroke="{_C_FACE_S}" stroke-width="{sw * 0.4:.3f}" opacity="0.65"/>'
            )
            out.append(
                f'<text x="{fcx:.3f}" y="{fcy:.3f}" font-size="{fs2:.3f}" '
                f'font-family="{_FONT}" font-style="italic" '
                f'text-anchor="middle" dominant-baseline="middle" '
                f'fill="{_C_FN}">f{fi}</text>'
            )
        if outer is not None:
            out.append(
                f'<text x="{_PAD * 0.82:.3f}" y="{_PAD * 0.82:.3f}" '
                f'font-size="{fs2:.3f}" font-family="{_FONT}" font-style="italic" '
                f'text-anchor="middle" dominant-baseline="middle" '
                f'fill="{_C_FN}">f∞</text>'
            )

    hl_e = {(u, v) for u, v in d.highlight_edges} | {(v, u) for u, v in d.highlight_edges}

    # ── Edges ─────────────────────────────────────────────────────────────────
    for u, v in d.edges:
        if u not in d.vertices or v not in d.vertices:
            continue
        x1, y1 = _sv(*d.vertices[u])
        x2, y2 = _sv(*d.vertices[v])
        is_hl  = (u, v) in hl_e
        col    = _C_E_HL if is_hl else _C_E

        if d.directed:
            sx, sy = _shorten(x2, y2, x1, y1, vr)
            ex, ey = _shorten(x1, y1, x2, y2, vr)
            mid    = 'g-arrow-hl' if is_hl else 'g-arrow'
            out.append(
                f'<line x1="{sx:.3f}" y1="{sy:.3f}" x2="{ex:.3f}" y2="{ey:.3f}" '
                f'stroke="{col}" stroke-width="{sw:.3f}" stroke-linecap="round" '
                f'marker-end="url(#{mid})"/>'
            )
        else:
            out.append(
                f'<line x1="{x1:.3f}" y1="{y1:.3f}" x2="{x2:.3f}" y2="{y2:.3f}" '
                f'stroke="{col}" stroke-width="{sw:.3f}" stroke-linecap="round"/>'
            )

        # Edge weight label
        wt = d.label_edge_weights.get(u + v) or d.label_edge_weights.get(v + u)
        if wt:
            mx, my = (x1 + x2) / 2, (y1 + y2) / 2
            dx, dy = x2 - x1, y2 - y1
            dn     = math.hypot(dx, dy) or 1.0
            nx, ny = -dy / dn, dx / dn          # left perpendicular
            if ny > 0:
                nx, ny = -nx, -ny               # keep label above the edge
            lx = mx + nx * fs2 * 1.5
            ly = my + ny * fs2 * 1.5
            out.append(
                f'<text x="{lx:.3f}" y="{ly:.3f}" font-size="{fs2:.3f}" '
                f'font-family="{_FONT}" text-anchor="middle" dominant-baseline="middle" '
                f'fill="{_C_WT}">{wt}</text>'
            )

    # ── Self-loops ─────────────────────────────────────────────────────────────
    lr = vr * 1.3
    for vname in d.loops:
        if vname not in d.vertices:
            continue
        cx, cy = _sv(*d.vertices[vname])
        col    = _C_E_HL if vname in d.highlight_vertices else _C_E
        out.append(
            f'<circle cx="{cx:.3f}" cy="{cy - vr - lr:.3f}" r="{lr:.3f}" '
            f'fill="none" stroke="{col}" stroke-width="{sw:.3f}"/>'
        )

    # ── Degree map ────────────────────────────────────────────────────────────
    deg: Dict[str, int] = {v: 0 for v in d.vertices}
    for u, v in d.edges:
        if u in deg:
            deg[u] += 1
        if v in deg:
            deg[v] += 1
    for v in d.loops:
        if v in deg:
            deg[v] += 2

    # Centroid for outward degree-label placement
    if d.label_degrees and d.vertices:
        all_sx = [_sv(*p)[0] for p in d.vertices.values()]
        all_sy = [_sv(*p)[1] for p in d.vertices.values()]
        gcx    = sum(all_sx) / len(all_sx)
        gcy    = sum(all_sy) / len(all_sy)
    else:
        gcx = gcy = _VB / 2

    # ── Vertices ──────────────────────────────────────────────────────────────
    # Degree labels are collected and emitted after all circles so they always
    # render on top of every vertex circle, not behind later-drawn ones.
    deg_labels: List[str] = []

    for vname, (ux, uy) in d.vertices.items():
        cx, cy = _sv(ux, uy)
        is_hl  = vname in d.highlight_vertices
        fill   = _C_V_HL if is_hl else _C_V

        out.append(
            f'<circle cx="{cx:.3f}" cy="{cy:.3f}" r="{vr:.3f}" '
            f'fill="{fill}" stroke="white" stroke-width="{sw * 0.7:.3f}"/>'
        )
        # Shrink font for multi-character labels
        lfs = fs * (1.0 if len(vname) <= 1 else 0.72 if len(vname) == 2 else 0.58)
        out.append(
            f'<text x="{cx:.3f}" y="{cy:.3f}" font-size="{lfs:.3f}" '
            f'font-family="{_FONT}" font-weight="600" '
            f'text-anchor="middle" dominant-baseline="middle" '
            f'fill="{_C_LAB}">{vname}</text>'
        )

        if d.label_degrees:
            ddx = cx - gcx
            ddy = cy - gcy
            ddn = math.hypot(ddx, ddy)
            if ddn < 1e-9:
                ddx, ddy = 0.0, -1.0
            else:
                ddx /= ddn
                ddy /= ddn
            # Place the label well clear of the vertex circle. The auto-zoom
            # viewBox expansion in the engine will pull any out-of-bounds labels
            # back into view, so no manual clamping is needed.
            dlx    = cx + ddx * (vr + fs2 * 1.25)
            dly    = cy + ddy * (vr + fs2 * 1.25)
            anchor = 'start' if ddx > 0.15 else ('end' if ddx < -0.15 else 'middle')
            deg_labels.append(
                f'<text x="{dlx:.3f}" y="{dly:.3f}" font-size="{fs2:.3f}" '
                f'font-family="{_FONT}" text-anchor="{anchor}" dominant-baseline="middle" '
                f'fill="{_C_DEG}">deg = {deg[vname]}</text>'
            )

    out.extend(deg_labels)
    return '\n'.join(out)
