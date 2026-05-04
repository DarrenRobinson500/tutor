import re
import math
from dataclasses import dataclass
from typing import Optional

DIAGRAM_TYPE = "Circle"

# ── Syntax ────────────────────────────────────────────────────────────────────
# Circle(radius: 5)
#
# Numeric/value labels (existing):
#   label_r: true      show radius line with numeric value  (default true)
#   label_d: true      show diameter line with numeric value (default false)
#
# Part labels — show the named part with the word "arc" / "chord" etc.:
#   show_arc: true     highlight an arc            (default false)
#   show_chord: true   draw a chord                (default false)
#   show_sector: true  shade a sector              (default false)
#   show_segment: true shade a segment             (default false)
#   show_tangent: true draw a tangent line         (default false)
#
# Angle parameters (degrees, CCW from positive x-axis):
#   angle1: 40         start of arc/chord/sector/segment (default 40)
#   angle2: 140        end   of arc/chord/sector/segment (default 140)
#   angle_t: 0         tangent contact point            (default 0 = rightmost)


@dataclass
class CircleDiagram:
    radius:        float = 1.0
    label_r:       bool  = True
    label_d:       bool  = False
    show_radius:   bool  = False   # highlight radius line, no numeric label
    show_diameter: bool  = False   # highlight diameter line, no numeric label
    show_arc:      bool  = False
    show_chord:    bool  = False
    show_sector:   bool  = False
    show_segment:  bool  = False
    show_tangent:  bool  = False
    show_labels:   bool  = True    # set false to hide word labels (arc, chord, etc.)
    angle1:        float = 40.0
    angle2:        float = 140.0
    angle_t:       float = 0.0


# ── Helpers ───────────────────────────────────────────────────────────────────

def _get_bool(line: str, key: str, default: bool) -> bool:
    m = re.search(rf'\b{key}:\s*(true|false|1|0)', line)
    return (m.group(1) in ('true', '1')) if m else default

def _get_num(line: str, key: str, default: float) -> float:
    m = re.search(rf'\b{key}:\s*(-?[\d.]+)', line)
    return float(m.group(1)) if m else default

def _pt(r: float, deg: float):
    """SVG point on a circle of radius r at angle deg (CCW from +x, y-flipped)."""
    rad = math.radians(deg)
    return r * math.cos(rad), -r * math.sin(rad)

def _arc_d(r: float, a1: float, a2: float) -> str:
    """SVG arc path data from angle a1 to a2 (going CCW, i.e. increasing angle)."""
    x1, y1 = _pt(r, a1)
    x2, y2 = _pt(r, a2)
    span = (a2 - a1) % 360
    large = 1 if span > 180 else 0
    # sweep=0 → counterclockwise in SVG screen space, which is CCW in our coord system
    return f"M{x1:.3f},{y1:.3f} A{r},{r} 0 {large} 0 {x2:.3f},{y2:.3f}"

def _fmt(n: float) -> str:
    return str(int(n)) if n == int(n) else f"{n:.4g}"

def _label(x, y, text, fs, anchor="middle", fill="#333"):
    return (
        f'<text x="{x:.3f}" y="{y:.3f}" font-size="{fs}" '
        f'font-family="system-ui, -apple-system, sans-serif" '
        f'text-anchor="{anchor}" dominant-baseline="middle" fill="{fill}">'
        f'{text}</text>'
    )


# ── Parse ─────────────────────────────────────────────────────────────────────

def parse(line: str) -> Optional[CircleDiagram]:
    if not line.strip().startswith("Circle"):
        return None
    m = re.search(r'\bradius:\s*([\d.]+)', line)
    if not m:
        return None
    return CircleDiagram(
        radius        = float(m.group(1)),
        label_r       = _get_bool(line, 'label_r',       True),
        label_d       = _get_bool(line, 'label_d',       False),
        show_radius   = _get_bool(line, 'show_radius',   False),
        show_diameter = _get_bool(line, 'show_diameter', False),
        show_arc      = _get_bool(line, 'show_arc',      False),
        show_chord    = _get_bool(line, 'show_chord',    False),
        show_sector   = _get_bool(line, 'show_sector',   False),
        show_segment  = _get_bool(line, 'show_segment',  False),
        show_tangent  = _get_bool(line, 'show_tangent',  False),
        show_labels   = _get_bool(line, 'show_labels',   True),
        angle1        = _get_num(line, 'angle1',  40.0),
        angle2        = _get_num(line, 'angle2', 140.0),
        angle_t       = _get_num(line, 'angle_t',  0.0),
    )


# ── Render ────────────────────────────────────────────────────────────────────

def render(d: CircleDiagram) -> str:
    R   = 11.0    # SVG radius
    sw  = 0.16    # thin stroke
    sw2 = sw * 3  # feature stroke
    fs  = 2.2     # font size for value labels
    fs2 = 2.4     # font size for word labels

    # Colours
    C_BLUE   = "#2563eb"
    C_GREEN  = "#16a34a"
    C_RED    = "#dc2626"
    C_GREY   = "#6b7280"

    out = []

    # ── Sector fill (behind circle outline) ──────────────────────────────────
    if d.show_sector:
        x1, y1 = _pt(R, d.angle1)
        x2, y2 = _pt(R, d.angle2)
        span = (d.angle2 - d.angle1) % 360
        large = 1 if span > 180 else 0
        out.append(
            f'<path d="M0,0 L{x1:.3f},{y1:.3f} A{R},{R} 0 {large} 0 {x2:.3f},{y2:.3f} Z" '
            f'fill="#dbeafe" stroke="none"/>'
        )

    # ── Segment fill (behind circle outline) ─────────────────────────────────
    if d.show_segment:
        x1, y1 = _pt(R, d.angle1)
        x2, y2 = _pt(R, d.angle2)
        span = (d.angle2 - d.angle1) % 360
        large = 1 if span > 180 else 0
        # Chord P1→P2, then return P2→P1 via the same (minor) arc reversed.
        # Forward arc is CCW (sweep=0); reversed = CW (sweep=1), same large flag.
        out.append(
            f'<path d="M{x1:.3f},{y1:.3f} L{x2:.3f},{y2:.3f} '
            f'A{R},{R} 0 {large} 1 {x1:.3f},{y1:.3f} Z" '
            f'fill="#dcfce7" stroke="none"/>'
        )

    # ── Circle outline ────────────────────────────────────────────────────────
    out.append(
        f'<circle cx="0" cy="0" r="{R}" fill="none" stroke="black" stroke-width="{sw}"/>'
    )

    # ── Centre dot ────────────────────────────────────────────────────────────
    out.append('<circle cx="0" cy="0" r="0.35" fill="black"/>')

    # ── Radius highlight (no numeric label) ──────────────────────────────────
    if d.show_radius:
        rx, ry = _pt(R, 45)
        out.append(
            f'<line x1="0" y1="0" x2="{rx:.3f}" y2="{ry:.3f}" '
            f'stroke="{C_BLUE}" stroke-width="{sw2}" stroke-linecap="round"/>'
        )
        out.append(f'<circle cx="{rx:.3f}" cy="{ry:.3f}" r="0.5" fill="{C_BLUE}"/>')
        if d.show_labels:
            lx, ly = _pt(R + 3.2, 45)
            out.append(_label(lx, ly, "radius", fs2, fill=C_BLUE))

    # ── Diameter highlight (no numeric label) ─────────────────────────────────
    if d.show_diameter:
        out.append(
            f'<line x1="{-R}" y1="0" x2="{R}" y2="0" '
            f'stroke="{C_BLUE}" stroke-width="{sw2}" stroke-linecap="round"/>'
        )
        for ex, ey in [(-R, 0), (R, 0)]:
            out.append(f'<circle cx="{ex:.3f}" cy="{ey:.3f}" r="0.5" fill="{C_BLUE}"/>')
        if d.show_labels:
            out.append(_label(0, -2.8, "diameter", fs2, fill=C_BLUE))

    # ── Arc ───────────────────────────────────────────────────────────────────
    if d.show_arc:
        x1, y1 = _pt(R, d.angle1)
        x2, y2 = _pt(R, d.angle2)
        span = (d.angle2 - d.angle1) % 360
        large = 1 if span > 180 else 0
        out.append(
            f'<path d="M{x1:.3f},{y1:.3f} A{R},{R} 0 {large} 0 {x2:.3f},{y2:.3f}" '
            f'fill="none" stroke="{C_BLUE}" stroke-width="{sw2}" stroke-linecap="round"/>'
        )
        # Endpoints
        for x, y in [(x1, y1), (x2, y2)]:
            out.append(f'<circle cx="{x:.3f}" cy="{y:.3f}" r="0.5" fill="{C_BLUE}"/>')
        if d.show_labels:
            mid_a = d.angle1 + span / 2
            lx, ly = _pt(R + 3.2, mid_a)
            out.append(_label(lx, ly, "arc", fs2, fill=C_BLUE))

    # ── Chord ─────────────────────────────────────────────────────────────────
    if d.show_chord:
        x1, y1 = _pt(R, d.angle1)
        x2, y2 = _pt(R, d.angle2)
        out.append(
            f'<line x1="{x1:.3f}" y1="{y1:.3f}" x2="{x2:.3f}" y2="{y2:.3f}" '
            f'stroke="{C_BLUE}" stroke-width="{sw2}" stroke-linecap="round"/>'
        )
        for x, y in [(x1, y1), (x2, y2)]:
            out.append(f'<circle cx="{x:.3f}" cy="{y:.3f}" r="0.5" fill="{C_BLUE}"/>')
        if d.show_labels:
            mx, my = (x1 + x2) / 2, (y1 + y2) / 2
            length = math.hypot(mx, my) or 1
            nx, ny = -mx / length, -my / length
            out.append(_label(mx + nx * 2.8, my + ny * 2.8, "chord", fs2, fill=C_BLUE))

    # ── Sector outline (radii + arc) ──────────────────────────────────────────
    if d.show_sector:
        x1, y1 = _pt(R, d.angle1)
        x2, y2 = _pt(R, d.angle2)
        span = (d.angle2 - d.angle1) % 360
        large = 1 if span > 180 else 0
        # Radii
        out.append(
            f'<line x1="0" y1="0" x2="{x1:.3f}" y2="{y1:.3f}" '
            f'stroke="{C_BLUE}" stroke-width="{sw2}"/>'
        )
        out.append(
            f'<line x1="0" y1="0" x2="{x2:.3f}" y2="{y2:.3f}" '
            f'stroke="{C_BLUE}" stroke-width="{sw2}"/>'
        )
        # Arc
        out.append(
            f'<path d="M{x1:.3f},{y1:.3f} A{R},{R} 0 {large} 0 {x2:.3f},{y2:.3f}" '
            f'fill="none" stroke="{C_BLUE}" stroke-width="{sw2}"/>'
        )
        if d.show_labels:
            mid_a = d.angle1 + span / 2
            lx, ly = _pt(R * 0.58, mid_a)
            out.append(_label(lx, ly, "sector", fs2, fill=C_BLUE))

    # ── Segment outline (chord + arc) ─────────────────────────────────────────
    if d.show_segment:
        x1, y1 = _pt(R, d.angle1)
        x2, y2 = _pt(R, d.angle2)
        span = (d.angle2 - d.angle1) % 360
        large = 1 if span > 180 else 0
        # Chord
        out.append(
            f'<line x1="{x1:.3f}" y1="{y1:.3f}" x2="{x2:.3f}" y2="{y2:.3f}" '
            f'stroke="{C_GREEN}" stroke-width="{sw2}" stroke-linecap="round"/>'
        )
        # Arc
        out.append(
            f'<path d="M{x1:.3f},{y1:.3f} A{R},{R} 0 {large} 0 {x2:.3f},{y2:.3f}" '
            f'fill="none" stroke="{C_GREEN}" stroke-width="{sw2}"/>'
        )
        if d.show_labels:
            mid_a = d.angle1 + span / 2
            lx, ly = _pt(R * 0.88, mid_a)
            out.append(_label(lx, ly, "segment", fs2, fill=C_GREEN))

    # ── Tangent ───────────────────────────────────────────────────────────────
    if d.show_tangent:
        rad_t = math.radians(d.angle_t)
        # Contact point
        tx, ty = R * math.cos(rad_t), -R * math.sin(rad_t)
        # Tangent direction: perpendicular to radius = (sin θ, cos θ) in SVG
        tdx, tdy = math.sin(rad_t), math.cos(rad_t)
        tlen = R * 0.85
        # Dashed radius line to contact point
        out.append(
            f'<line x1="0" y1="0" x2="{tx:.3f}" y2="{ty:.3f}" '
            f'stroke="{C_GREY}" stroke-width="{sw2}" stroke-dasharray="0.8,0.6"/>'
        )
        # Tangent line
        out.append(
            f'<line x1="{tx - tdx*tlen:.3f}" y1="{ty - tdy*tlen:.3f}" '
            f'x2="{tx + tdx*tlen:.3f}" y2="{ty + tdy*tlen:.3f}" '
            f'stroke="{C_RED}" stroke-width="{sw2}" stroke-linecap="round"/>'
        )
        # Right-angle marker at contact point
        s = 1.2  # marker size
        # Two legs of the right-angle square: along radius dir and along tangent dir
        rdx, rdy = math.cos(rad_t), -math.sin(rad_t)
        out.append(
            f'<polyline points="'
            f'{tx - rdx*s:.3f},{ty - rdy*s:.3f} '
            f'{tx - rdx*s + tdx*s:.3f},{ty - rdy*s + tdy*s:.3f} '
            f'{tx + tdx*s:.3f},{ty + tdy*s:.3f}" '
            f'fill="none" stroke="{C_GREY}" stroke-width="{sw}"/>'
        )
        # Contact point dot
        out.append(f'<circle cx="{tx:.3f}" cy="{ty:.3f}" r="0.5" fill="{C_RED}"/>')
        if d.show_labels:
            lx = tx + tdx * (tlen + 2.5)
            ly = ty + tdy * (tlen + 2.5)
            out.append(_label(lx, ly, "tangent", fs2, fill=C_RED))

    # ── Existing radius / diameter labels ─────────────────────────────────────
    if d.label_r and d.label_d:
        # Diameter: horizontal
        out.append(
            f'<line x1="{-R}" y1="0" x2="{R}" y2="0" stroke="black" stroke-width="{sw}"/>'
        )
        out.append(_label(0, 1.8, _fmt(d.radius * 2), fs))
        # Radius: 45° upward-right
        rx, ry = _pt(R, 45)
        out.append(
            f'<line x1="0" y1="0" x2="{rx:.3f}" y2="{ry:.3f}" stroke="black" stroke-width="{sw}"/>'
        )
        out.append(_label(rx / 2 - 1.5, ry / 2 - 1.0, _fmt(d.radius), fs))

    elif d.label_d:
        out.append(
            f'<line x1="{-R}" y1="0" x2="{R}" y2="0" stroke="black" stroke-width="{sw}"/>'
        )
        out.append(_label(0, -1.8, _fmt(d.radius * 2), fs))

    elif d.label_r:
        out.append(
            f'<line x1="0" y1="0" x2="{R}" y2="0" stroke="black" stroke-width="{sw}"/>'
        )
        out.append(_label(R / 2, -1.8, _fmt(d.radius), fs))

    return "\n".join(out)
