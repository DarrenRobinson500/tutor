import re
import math
from dataclasses import dataclass, field
from typing import List, Optional, Tuple

DIAGRAM_TYPE = "CompositeSolid"
SUPPORTS_VIZ_SCALE = True

# Syntax:
#   CompositeSolid(rect_prism(w:4, h:2, d:3), half_cylinder(r:2, length:4, on:top))
#   CompositeSolid(rect_prism(w:4, h:2, d:3), cylinder(r:1, h:2, on:top))
#   CompositeSolid(rect_prism(w:4, h:2, d:3), cone(r:2, h:3, on:top))
#
# Shape primitives:
#   rect_prism(w, h, d)             rectangular prism
#   half_cylinder(r, length, axis)  half-cylinder; axis: x (default) or z
#   cylinder(r, h)                  full cylinder
#   cone(r, h)                      cone
#
# Positioning:
#   on: top | front | right         stack relative to current bounding box
#   at: x,y,z                       absolute position of shape origin
#
# labels: true (default) — dimension labels on edges

_SW = 0.18   # base stroke width
_FS = 2.2    # base font size

# ── Oblique projection ────────────────────────────────────────────────────────
# (x, y, z) → screen (sx, sy)  where y is up, z goes back-right
_OX = 0.35
_OY = 0.35

def _proj(x: float, y: float, z: float) -> Tuple[float, float]:
    return (x + z * _OX, -(y + z * _OY))


# ── Face dataclass ────────────────────────────────────────────────────────────
@dataclass
class Face:
    verts: List[Tuple[float, float, float]]   # 3-D vertices (CCW when facing viewer)
    fill: str
    tag: str = ""          # for edge suppression
    normal: Optional[Tuple[float, float, float]] = None   # outward normal (3-D)

    def projected(self) -> List[Tuple[float, float]]:
        return [_proj(x, y, z) for x, y, z in self.verts]

    def avg_depth(self) -> float:
        """Painter's-algorithm depth: project each vertex and average."""
        return sum(_proj(x, y, z)[1] for x, y, z in self.verts) / len(self.verts)

    def is_visible(self) -> bool:
        if self.normal is None:
            return True
        nx, ny, nz = self.normal
        # Projection: sx = x + z*_OX, sy = -(y + z*_OY)
        # Null-space of projection → viewer direction = (-_OX, -_OY, +1)
        dot = nx * (-_OX) + ny * (-_OY) + nz * 1.0
        return dot >= -0.01


# ── Shape colours ─────────────────────────────────────────────────────────────
_COL_TOP   = "#e8f4f8"
_COL_FRONT = "#d0dde8"
_COL_SIDE  = "#b8ccd8"
_COL_CURVE = "#c8d8e8"


# ── Primitive builders ────────────────────────────────────────────────────────

def _rect_prism_faces(w: float, h: float, d: float, ox: float, oy: float, oz: float) -> List[Face]:
    """Axis-aligned box at offset (ox,oy,oz), dimensions w(x) × h(y) × d(z)."""
    x0, x1 = ox, ox + w
    y0, y1 = oy, oy + h
    z0, z1 = oz, oz + d
    return [
        Face([(x0,y1,z0),(x1,y1,z0),(x1,y1,z1),(x0,y1,z1)], _COL_TOP,   "top",    ( 0, 1, 0)),
        Face([(x0,y0,z1),(x1,y0,z1),(x1,y1,z1),(x0,y1,z1)], _COL_FRONT, "front",  ( 0, 0, 1)),
        Face([(x1,y0,z0),(x1,y0,z1),(x1,y1,z1),(x1,y1,z0)], _COL_SIDE,  "right",  ( 1, 0, 0)),
        Face([(x0,y0,z0),(x0,y0,z1),(x1,y0,z1),(x1,y0,z0)], _COL_SIDE,  "bottom", ( 0,-1, 0)),
        Face([(x0,y0,z0),(x1,y0,z0),(x1,y1,z0),(x0,y1,z0)], _COL_SIDE,  "back",   ( 0, 0,-1)),
        Face([(x0,y0,z0),(x0,y1,z0),(x0,y1,z1),(x0,y0,z1)], _COL_SIDE,  "left",   (-1, 0, 0)),
    ]


def _half_cylinder_faces(r: float, length: float, axis: str,
                          ox: float, oy: float, oz: float,
                          n_segs: int = 16) -> List[Face]:
    """
    Upper half-cylinder (flat face at y=oy, curved cap upward).
    axis='x': length runs along x (default for "on top of rect_prism with length=w")
    axis='z': length runs along z
    """
    faces: List[Face] = []
    angles = [math.pi * i / n_segs for i in range(n_segs + 1)]

    if axis == 'x':
        x0, x1 = ox, ox + length
        # Curved strip faces
        for i in range(n_segs):
            a0, a1 = angles[i], angles[i + 1]
            y0c = oy + r * math.sin(a0);  z0c = oz + r * math.cos(a0)
            y1c = oy + r * math.sin(a1);  z1c = oz + r * math.cos(a1)
            mid_a = (a0 + a1) / 2
            ny = math.sin(mid_a); nz = math.cos(mid_a)
            faces.append(Face(
                [(x0, y0c, z0c), (x1, y0c, z0c), (x1, y1c, z1c), (x0, y1c, z1c)],
                _COL_CURVE, f"curve_{i}", (0, ny, nz)
            ))
        # Flat bottom rectangle
        faces.append(Face(
            [(x0, oy, oz - r), (x1, oy, oz - r), (x1, oy, oz + r), (x0, oy, oz + r)],
            _COL_FRONT, "flat", (0, -1, 0)
        ))
        # End caps (semicircles, approximated as fans)
        for xc, nx_n in [(x0, -1), (x1, 1)]:
            fan = [(xc, oy, oz)] + [(xc, oy + r * math.sin(a), oz + r * math.cos(a)) for a in angles]
            for i in range(n_segs):
                mid_a = (angles[i] + angles[i+1]) / 2
                faces.append(Face(
                    [fan[0], fan[i + 1], fan[i + 2]],
                    _COL_SIDE, f"cap_{i}", (nx_n, 0, 0)
                ))
    else:  # axis='z'
        z0_end, z1_end = oz, oz + length
        for i in range(n_segs):
            a0, a1 = angles[i], angles[i + 1]
            x0c = ox + r * math.cos(a0);  y0c = oy + r * math.sin(a0)
            x1c = ox + r * math.cos(a1);  y1c = oy + r * math.sin(a1)
            mid_a = (a0 + a1) / 2
            nx_n = math.cos(mid_a); ny = math.sin(mid_a)
            faces.append(Face(
                [(x0c, y0c, z0_end), (x0c, y0c, z1_end), (x1c, y1c, z1_end), (x1c, y1c, z0_end)],
                _COL_CURVE, f"curve_{i}", (nx_n, ny, 0)
            ))
        faces.append(Face(
            [(ox - r, oy, z0_end), (ox + r, oy, z0_end), (ox + r, oy, z1_end), (ox - r, oy, z1_end)],
            _COL_FRONT, "flat", (0, -1, 0)
        ))
        for zc, nz_n in [(z0_end, -1), (z1_end, 1)]:
            fan = [(ox, oy, zc)] + [(ox + r * math.cos(a), oy + r * math.sin(a), zc) for a in angles]
            for i in range(n_segs):
                faces.append(Face(
                    [fan[0], fan[i + 1], fan[i + 2]],
                    _COL_SIDE, f"cap_{i}", (0, 0, nz_n)
                ))
    return faces


def _cylinder_faces(r: float, h: float, ox: float, oy: float, oz: float,
                    n_segs: int = 20) -> List[Face]:
    faces: List[Face] = []
    angles = [2 * math.pi * i / n_segs for i in range(n_segs + 1)]
    for i in range(n_segs):
        a0, a1 = angles[i], angles[i + 1]
        x0c = ox + r * math.cos(a0);  z0c = oz + r * math.sin(a0)
        x1c = ox + r * math.cos(a1);  z1c = oz + r * math.sin(a1)
        mid_a = (a0 + a1) / 2
        nx_n = math.cos(mid_a); nz_n = math.sin(mid_a)
        faces.append(Face(
            [(x0c, oy, z0c), (x0c, oy + h, z0c), (x1c, oy + h, z1c), (x1c, oy, z1c)],
            _COL_FRONT, f"side_{i}", (nx_n, 0, nz_n)
        ))
    # Top disc
    top_pts = [(ox + r * math.cos(a), oy + h, oz + r * math.sin(a)) for a in angles[:-1]]
    for i in range(n_segs):
        faces.append(Face(
            [(ox, oy + h, oz), top_pts[i], top_pts[(i + 1) % n_segs]],
            _COL_TOP, f"top_{i}", (0, 1, 0)
        ))
    # Bottom disc
    bot_pts = [(ox + r * math.cos(a), oy, oz + r * math.sin(a)) for a in angles[:-1]]
    for i in range(n_segs):
        faces.append(Face(
            [(ox, oy, oz), bot_pts[(i + 1) % n_segs], bot_pts[i]],
            _COL_SIDE, f"bot_{i}", (0, -1, 0)
        ))
    return faces


def _cone_faces(r: float, h: float, ox: float, oy: float, oz: float,
                n_segs: int = 20) -> List[Face]:
    faces: List[Face] = []
    angles = [2 * math.pi * i / n_segs for i in range(n_segs + 1)]
    slant = math.hypot(r, h)
    for i in range(n_segs):
        a0, a1 = angles[i], angles[i + 1]
        x0c = ox + r * math.cos(a0);  z0c = oz + r * math.sin(a0)
        x1c = ox + r * math.cos(a1);  z1c = oz + r * math.sin(a1)
        mid_a = (a0 + a1) / 2
        nx_n = h / slant * math.cos(mid_a)
        ny_n = r / slant
        nz_n = h / slant * math.sin(mid_a)
        faces.append(Face(
            [(ox, oy + h, oz), (x1c, oy, z1c), (x0c, oy, z0c)],
            _COL_FRONT, f"side_{i}", (nx_n, ny_n, nz_n)
        ))
    bot_pts = [(ox + r * math.cos(a), oy, oz + r * math.sin(a)) for a in angles[:-1]]
    for i in range(n_segs):
        faces.append(Face(
            [(ox, oy, oz), bot_pts[(i + 1) % n_segs], bot_pts[i]],
            _COL_SIDE, f"bot_{i}", (0, -1, 0)
        ))
    return faces


# ── Shape spec dataclass ──────────────────────────────────────────────────────

@dataclass
class ShapeSpec:
    kind: str
    w: float = 4.0
    h: float = 2.0
    d: float = 3.0
    r: float = 1.0
    length: float = 0.0   # half_cylinder length (defaults to w of base)
    axis: str = "x"
    on: str = ""          # "top", "front", "right"
    at: Optional[Tuple[float, float, float]] = None


@dataclass
class CompositeSolidDiagram:
    shapes: List[ShapeSpec] = field(default_factory=list)
    labels: bool = True


# ── Parser ────────────────────────────────────────────────────────────────────

def _parse_inner(inner: str) -> ShapeSpec:
    """Parse the inside of a shape call like `rect_prism(w:4, h:2, d:3)`."""
    def get_num(key, default):
        m = re.search(rf'\b{key}\s*[:=]\s*([\d.]+)', inner)
        return float(m.group(1)) if m else default

    def get_str(key, default=""):
        m = re.search(rf'\b{key}\s*[:=]\s*"([^"]*)"', inner)
        if m: return m.group(1)
        m = re.search(rf'\b{key}\s*[:=]\s*([^,)\s]+)', inner)
        return m.group(1) if m else default

    kind_m = re.match(r'\s*(\w+)\s*\(', inner)
    kind = kind_m.group(1) if kind_m else "rect_prism"

    at_val = None
    at_m = re.search(r'\bat\s*[:=]\s*([\d.-]+)\s*,\s*([\d.-]+)\s*,\s*([\d.-]+)', inner)
    if at_m:
        at_val = (float(at_m.group(1)), float(at_m.group(2)), float(at_m.group(3)))

    return ShapeSpec(
        kind=kind,
        w=get_num("w", 4.0),
        h=get_num("h", 2.0),
        d=get_num("d", 3.0),
        r=get_num("r", 1.0),
        length=get_num("length", 0.0),
        axis=get_str("axis", "x"),
        on=get_str("on", ""),
        at=at_val,
    )


def _split_top_level(s: str) -> List[str]:
    """Split string by top-level commas (not inside parentheses)."""
    parts, current, depth = [], [], 0
    for ch in s:
        if ch == '(':
            depth += 1
            current.append(ch)
        elif ch == ')':
            depth -= 1
            current.append(ch)
        elif ch == ',' and depth == 0:
            seg = ''.join(current).strip()
            if seg:
                parts.append(seg)
            current = []
        else:
            current.append(ch)
    seg = ''.join(current).strip()
    if seg:
        parts.append(seg)
    return parts


def parse(line: str) -> Optional[CompositeSolidDiagram]:
    m = re.match(r'CompositeSolid\s*\((.+)\)\s*$', line.strip(), re.DOTALL)
    if not m:
        return None

    inner = m.group(1)

    labels_m = re.search(r'\blabels:\s*(true|false)', inner)
    labels = (labels_m.group(1) != 'false') if labels_m else True

    # Split on top-level commas to get individual shape specs
    parts = _split_top_level(inner)

    shapes = []
    for part in parts:
        part = part.strip()
        if re.match(r'labels\s*[:=]', part):
            continue
        if re.match(r'\w+\s*\(', part):
            shapes.append(_parse_inner(part))

    if not shapes:
        return None

    return CompositeSolidDiagram(shapes=shapes, labels=labels)


# ── Layout engine ─────────────────────────────────────────────────────────────

def _shape_bbox(spec: ShapeSpec) -> Tuple[float, float, float, float, float, float]:
    """Return (x0,y0,z0, x1,y1,z1) bounding box of shape at origin."""
    k = spec.kind
    if k == "rect_prism":
        return (0, 0, 0, spec.w, spec.h, spec.d)
    elif k == "half_cylinder":
        length = spec.length if spec.length > 0 else spec.w
        r = spec.r
        if spec.axis == 'x':
            return (0, 0, -r, length, r, r)
        else:
            return (-r, 0, 0, r, r, length)
    elif k == "cylinder":
        return (-spec.r, 0, -spec.r, spec.r, spec.h, spec.r)
    elif k == "cone":
        return (-spec.r, 0, -spec.r, spec.r, spec.h, spec.r)
    return (0, 0, 0, spec.w, spec.h, spec.d)


def _compute_offsets(shapes: List[ShapeSpec]) -> List[Tuple[float, float, float]]:
    """Compute (ox, oy, oz) world offset for each shape."""
    offsets: List[Tuple[float, float, float]] = []
    # Accumulated bounding box of all placed shapes (world coords)
    bb_x0, bb_y0, bb_z0 = 0.0, 0.0, 0.0
    bb_x1, bb_y1, bb_z1 = 0.0, 0.0, 0.0

    for i, spec in enumerate(shapes):
        if spec.at is not None:
            ox, oy, oz = spec.at
        elif spec.on == "top" and i > 0:
            lx0, ly0, lz0, lx1, ly1, lz1 = _shape_bbox(spec)
            ox = (bb_x0 + bb_x1) / 2 - (lx0 + lx1) / 2
            oy = bb_y1
            oz = (bb_z0 + bb_z1) / 2 - (lz0 + lz1) / 2
        elif spec.on == "front" and i > 0:
            lx0, ly0, lz0, lx1, ly1, lz1 = _shape_bbox(spec)
            ox = (bb_x0 + bb_x1) / 2 - (lx0 + lx1) / 2
            oy = bb_y0
            oz = bb_z1
        elif spec.on == "right" and i > 0:
            lx0, ly0, lz0, lx1, ly1, lz1 = _shape_bbox(spec)
            ox = bb_x1
            oy = bb_y0
            oz = (bb_z0 + bb_z1) / 2 - (lz0 + lz1) / 2
        else:
            ox, oy, oz = 0.0, 0.0, 0.0

        offsets.append((ox, oy, oz))

        # Update accumulated bounding box
        lx0, ly0, lz0, lx1, ly1, lz1 = _shape_bbox(spec)
        wx0, wy0, wz0 = ox + lx0, oy + ly0, oz + lz0
        wx1, wy1, wz1 = ox + lx1, oy + ly1, oz + lz1
        if i == 0:
            bb_x0, bb_y0, bb_z0 = wx0, wy0, wz0
            bb_x1, bb_y1, bb_z1 = wx1, wy1, wz1
        else:
            bb_x0 = min(bb_x0, wx0); bb_y0 = min(bb_y0, wy0); bb_z0 = min(bb_z0, wz0)
            bb_x1 = max(bb_x1, wx1); bb_y1 = max(bb_y1, wy1); bb_z1 = max(bb_z1, wz1)

    return offsets


# ── SVG rendering helpers ─────────────────────────────────────────────────────

def _polygon_svg(pts2d: List[Tuple[float, float]], fill: str, sw: float) -> str:
    pts_str = " ".join(f"{x:.3f},{y:.3f}" for x, y in pts2d)
    return (f'<polygon points="{pts_str}" fill="{fill}" '
            f'stroke="#5a7a9a" stroke-width="{sw:.3f}" stroke-linejoin="round"/>')


def _label_svg(x: float, y: float, text: str, fs: float) -> str:
    return (f'<text x="{x:.3f}" y="{y:.3f}" font-size="{fs:.3f}" '
            f'font-family="system-ui,-apple-system,sans-serif" '
            f'text-anchor="middle" dominant-baseline="middle">{text}</text>')


def _fmt(n: float) -> str:
    return str(int(n)) if n == int(n) else f"{n:g}"


def _edge_midpoint_label(p1: Tuple[float, float, float], p2: Tuple[float, float, float],
                          text: str, fs: float, offset: float = 1.5) -> str:
    """Label at the midpoint of a 3-D edge, offset slightly outward in screen space."""
    mx, my, mz = (p1[0] + p2[0]) / 2, (p1[1] + p2[1]) / 2, (p1[2] + p2[2]) / 2
    sx, sy = _proj(mx, my, mz)
    # Offset: push label slightly above in screen y
    return _label_svg(sx + offset * 0.2, sy - offset, text, fs)


# ── Main render ───────────────────────────────────────────────────────────────

def render(d: CompositeSolidDiagram, viz_scale: float = 1.0) -> str:
    sw = _SW * viz_scale
    fs = _FS * viz_scale

    offsets = _compute_offsets(d.shapes)

    all_faces: List[Face] = []

    for spec, (ox, oy, oz) in zip(d.shapes, offsets):
        k = spec.kind
        if k == "rect_prism":
            all_faces += _rect_prism_faces(spec.w, spec.h, spec.d, ox, oy, oz)
        elif k == "half_cylinder":
            length = spec.length if spec.length > 0 else spec.w
            all_faces += _half_cylinder_faces(spec.r, length, spec.axis, ox, oy, oz)
        elif k == "cylinder":
            all_faces += _cylinder_faces(spec.r, spec.h, ox, oy, oz)
        elif k == "cone":
            all_faces += _cone_faces(spec.r, spec.h, ox, oy, oz)

    # Filter invisible faces, sort by depth (painter's algorithm)
    visible_faces = [f for f in all_faces if f.is_visible()]
    visible_faces.sort(key=lambda f: f.avg_depth())

    out = []
    for face in visible_faces:
        pts2d = face.projected()
        out.append(_polygon_svg(pts2d, face.fill, sw))

    # Labels only on pass 2 (viz_scale != 1.0) so text bbox doesn't skew auto-zoom
    if viz_scale != 1.0 and d.labels:
        _add_labels(d.shapes, offsets, out, fs)

    return "\n".join(out)


def _add_labels(shapes: List[ShapeSpec], offsets, out: List[str], fs: float):
    """Add edge labels for rect_prism shapes."""
    for spec, (ox, oy, oz) in zip(shapes, offsets):
        if spec.kind != "rect_prism":
            continue
        w, h, d_val = spec.w, spec.h, spec.d
        # Width label: bottom-front edge
        p1 = (ox, oy, oz + d_val); p2 = (ox + w, oy, oz + d_val)
        out.append(_edge_midpoint_label(p1, p2, _fmt(w), fs))
        # Height label: front-right edge
        p1 = (ox + w, oy, oz + d_val); p2 = (ox + w, oy + h, oz + d_val)
        out.append(_edge_midpoint_label(p1, p2, _fmt(h), fs, offset=2.0))
        # Depth label: bottom-right edge
        p1 = (ox + w, oy, oz); p2 = (ox + w, oy, oz + d_val)
        out.append(_edge_midpoint_label(p1, p2, _fmt(d_val), fs, offset=2.0))
