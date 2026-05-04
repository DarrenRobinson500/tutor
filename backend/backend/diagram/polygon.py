import re
import math
from dataclasses import dataclass, field
from typing import Optional, List, Tuple

DIAGRAM_TYPE = "Polygon"

# Syntax: Polygon(sides: [5, 5, 5, 4, 3], pos: (x, y), scale: 1.5, labels: true, name: "")
#         Polygon(angles: [60, 120, 60, 120], label_angles: [60°, 120°, 60°, 120°])
#         Polygon(sides: [4, 6, 4, 6], angles: [60, 120, 60, 120], labels: true)
#
# sides        — list of side lengths, one per side (3 or more).
#                Optional when angles is provided; defaults to all 1.0.
# angles       — interior angles in degrees, one per vertex.
#                If omitted, equal interior angles are used (regular polygon shape).
# label_angles — text labels shown at each vertex with an arc marker.
#                Can be plain values, variable expressions (already substituted),
#                or empty strings to suppress a label.
#                A right-angle (≈90°) vertex gets a square marker instead of a curved arc.
# pos          — centre position in SVG units (default 0, 0)
# scale        — size multiplier; omit for auto-scaling to fit the canvas
# labels       — true (default) shows each side length; false hides them
# name         — optional text shown at the centre of the polygon


@dataclass
class PolygonDiagram:
    sides: List[float]
    angles: Optional[List[float]] = None      # interior angles in degrees, one per vertex
    label_angles: Optional[List[str]] = None  # angle labels at each vertex
    pos: Tuple[float, float] = (0.0, 0.0)
    scale: float = 0.0   # 0 = auto-scale
    labels: bool = True
    name: str = ""


def parse(line: str) -> Optional[PolygonDiagram]:
    if not line.strip().startswith("Polygon"):
        return None

    # ── angles ────────────────────────────────────────────────────────────────
    angles_match = re.search(r'\bangles:\s*\[([^\]]*)\]', line)
    angles: Optional[List[float]] = None
    if angles_match:
        try:
            angles = [float(s.strip()) for s in angles_match.group(1).split(',') if s.strip()]
        except ValueError:
            return None

    # ── sides (optional when angles given) ───────────────────────────────────
    sides_match = re.search(r'\bsides:\s*\[([^\]]+)\]', line)
    sides: Optional[List[float]] = None
    if sides_match:
        try:
            sides = [float(s.strip()) for s in sides_match.group(1).split(',') if s.strip()]
        except ValueError:
            return None

    if sides is None and angles is None:
        return None

    # Default to unit sides when only angles are given
    if sides is None:
        sides = [1.0] * len(angles)

    if len(sides) < 3:
        return None
    if angles is not None and len(angles) != len(sides):
        return None

    # ── label_angles ──────────────────────────────────────────────────────────
    label_angles: Optional[List[str]] = None
    la_match = re.search(r'\blabel_angles:\s*\[([^\]]*)\]', line)
    if la_match:
        parts = [s.strip() for s in la_match.group(1).split(',')]
        # Pad/trim to match number of vertices
        while len(parts) < len(sides):
            parts.append('')
        label_angles = parts[:len(sides)]

    # ── other parameters ──────────────────────────────────────────────────────
    pos_match = re.search(r'\bpos:\s*\(\s*(-?[\d.]+)\s*,\s*(-?[\d.]+)\s*\)', line)
    pos = (float(pos_match.group(1)), float(pos_match.group(2))) if pos_match else (0.0, 0.0)

    scale_match = re.search(r'\bscale:\s*([\d.]+)', line)
    scale = float(scale_match.group(1)) if scale_match else 0.0

    labels_match = re.search(r'\blabels:\s*(true|false)', line)
    labels = (labels_match.group(1) != 'false') if labels_match else True

    name_match = re.search(r'\bname:\s*["\']([^"\']*)["\']', line)
    name = name_match.group(1) if name_match else ""

    return PolygonDiagram(sides=sides, angles=angles, label_angles=label_angles,
                          pos=pos, scale=scale, labels=labels, name=name)


def _exterior_angles(n: int, angles: Optional[List[float]]) -> List[float]:
    """Return exterior angle (radians) at each vertex."""
    if angles is not None:
        return [math.pi - math.radians(a) for a in angles]
    return [2 * math.pi / n] * n


def _build_vertices(sides: List[float], scale: float, pos: Tuple[float, float],
                    angles: Optional[List[float]] = None) -> List[Tuple[float, float]]:
    """
    Place vertices using the given (or equal) exterior angles.
    The first side runs left-to-right.  The polygon is centred on pos.
    """
    n = len(sides)
    exts = _exterior_angles(n, angles)

    direction = 0.0
    x, y = 0.0, 0.0
    verts: List[Tuple[float, float]] = [(x, y)]

    for i in range(n - 1):
        length = sides[i] * scale
        x += length * math.cos(direction)
        y += length * math.sin(direction)
        verts.append((x, y))
        direction -= exts[(i + 1) % n]

    cx_c = sum(v[0] for v in verts) / n
    cy_c = sum(v[1] for v in verts) / n
    px, py = pos
    return [(v[0] + px - cx_c, v[1] + py - cy_c) for v in verts]


def _auto_scale(sides: List[float], angles: Optional[List[float]] = None) -> float:
    """Return a scale so the polygon spans about 20 SVG units on its longest axis."""
    n = len(sides)
    exts = _exterior_angles(n, angles)
    direction = 0.0
    x, y = 0.0, 0.0
    xs, ys = [x], [y]
    for i in range(n - 1):
        x += sides[i] * math.cos(direction)
        y += sides[i] * math.sin(direction)
        xs.append(x)
        ys.append(y)
        direction -= exts[(i + 1) % n]
    w = max(xs) - min(xs)
    h = max(ys) - min(ys)
    return 20.0 / max(w, h, 1.0)


def _fmt(n: float) -> str:
    return str(int(n)) if n == int(n) else f"{n:.4g}"


_ARC_R = 1.8      # radius of angle arc markers
_ARC_SW = 0.13    # arc stroke-width
_FONT_SIZE = 2.0  # angle label font size


def _angle_arc(verts: List[Tuple[float, float]], i: int, label: str) -> str:
    """
    Draw an angle arc (or square marker for 90°) and optional label at vertex i.
    The arc spans the interior angle between the two adjacent edges.
    """
    n = len(verts)
    cx, cy = verts[i]
    nx, ny = verts[(i + 1) % n]
    px, py = verts[(i - 1) % n]

    # Angles from vertex to neighbours (math y-up convention, y-flipped from SVG)
    ang_to_next = math.atan2(-(ny - cy), nx - cx)
    ang_to_prev = math.atan2(-(py - cy), px - cx)

    # CCW sweep in math (= interior angle for a CCW-traced convex polygon)
    span = (ang_to_prev - ang_to_next) % (2 * math.pi)

    r = _ARC_R
    frags = []

    if abs(span - math.pi / 2) < 0.01:   # ≈ 90° → square corner marker
        s_rad, e_rad = ang_to_next, ang_to_prev
        ux0 = math.cos(s_rad);  uy0 = -math.sin(s_rad)   # SVG y-flip
        ux1 = math.cos(e_rad);  uy1 = -math.sin(e_rad)
        p0x = cx + r * ux0;   p0y = cy + r * uy0
        p1x = cx + r * (ux0 + ux1);  p1y = cy + r * (uy0 + uy1)
        p2x = cx + r * ux1;   p2y = cy + r * uy1
        frags.append(
            f'<path d="M{p0x:.3f},{p0y:.3f} L{p1x:.3f},{p1y:.3f} L{p2x:.3f},{p2y:.3f}" '
            f'fill="none" stroke="black" stroke-width="{_ARC_SW}" '
            f'stroke-linejoin="miter" stroke-linecap="butt"/>'
        )
    else:
        large = 1 if span > math.pi else 0
        ax0 = cx + r * math.cos(ang_to_next);  ay0 = cy - r * math.sin(ang_to_next)
        ax1 = cx + r * math.cos(ang_to_prev);  ay1 = cy - r * math.sin(ang_to_prev)
        frags.append(
            f'<path d="M{ax0:.3f},{ay0:.3f} A{r:.3f},{r:.3f} 0 {large},0 {ax1:.3f},{ay1:.3f}" '
            f'fill="none" stroke="black" stroke-width="{_ARC_SW}"/>'
        )

    if label:
        bis_ang = ang_to_next + span / 2   # bisector (math y-up convention)
        label_r = r + 1.6
        lx = cx + label_r * math.cos(bis_ang)
        ly = cy - label_r * math.sin(bis_ang)   # back to SVG y-down
        frags.append(
            f'<text x="{lx:.3f}" y="{ly:.3f}" text-anchor="middle" '
            f'dominant-baseline="middle" font-size="{_FONT_SIZE}" '
            f'font-family="system-ui,-apple-system,sans-serif" fill="black">{label}</text>'
        )

    return "\n".join(frags)


def render(d: PolygonDiagram) -> str:
    scale = d.scale if d.scale > 0 else _auto_scale(d.sides, d.angles)
    verts = _build_vertices(d.sides, scale, d.pos, d.angles)
    n = len(verts)

    sw = 0.16
    font_size = 2.0

    cx = sum(v[0] for v in verts) / n
    cy = sum(v[1] for v in verts) / n

    frags: List[str] = []

    # Polygon outline
    pts = " ".join(f"{v[0]:.3f},{v[1]:.3f}" for v in verts)
    frags.append(
        f'<polygon points="{pts}" fill="none" stroke="black" stroke-width="{sw}"/>'
    )

    # Side labels
    if d.labels:
        for i in range(n):
            v1 = verts[i]
            v2 = verts[(i + 1) % n]
            mx = (v1[0] + v2[0]) / 2
            my = (v1[1] + v2[1]) / 2
            dx = mx - cx
            dy = my - cy
            dist = math.hypot(dx, dy) or 1.0
            offset = font_size * 1.3
            lx = mx + dx / dist * offset
            ly = my + dy / dist * offset
            frags.append(
                f'<text x="{lx:.3f}" y="{ly:.3f}" font-size="{font_size}" '
                f'font-family="system-ui, -apple-system, sans-serif" text-anchor="middle" '
                f'dominant-baseline="middle" fill="#333">{_fmt(d.sides[i])}</text>'
            )

    # Angle arcs and labels
    if d.label_angles is not None:
        for i, label in enumerate(d.label_angles):
            arc_svg = _angle_arc(verts, i, label)
            if arc_svg:
                frags.append(arc_svg)

    # Name in centre
    if d.name:
        frags.append(
            f'<text x="{cx:.3f}" y="{cy:.3f}" font-size="{font_size}" '
            f'font-family="system-ui, -apple-system, sans-serif" text-anchor="middle" '
            f'dominant-baseline="middle" fill="#555">{d.name}</text>'
        )

    return "\n".join(frags)
