import re
import math
from dataclasses import dataclass, field
from typing import List, Optional

DIAGRAM_TYPE = "Triangle"
SUPPORTS_VIZ_SCALE = True   # engine passes a global viz_scale after computing combined bbox

# Syntax: Triangle(a: 5, b: 7, A: 60)
# Specify any valid combination of sides a,b,c and angles A,B,C (degrees).
# Valid cases: SSS, SAS, ASA, AAS, AA — SSA is rejected as ambiguous.
#
# Decorators (all optional):
#   ticks_a/b/c: 1-3        tick marks on sides
#   arcs_A/B/C: 1-3         angle arcs at vertices
#   label_A/B/C: "60°"      angle labels (manual)
#   label_a/b/c: "5"        side labels (manual)
#   label_v: true            auto-label sides with their numeric values
#   angle_labels: true       auto-label given angles with their degree values
#   pos: (x, y)              centre offset
#   scale: 1.5               scale factor


@dataclass
class TriangleDiagram:
    a: float
    b: float
    c: float
    ticks_a: int = 0
    ticks_b: int = 0
    ticks_c: int = 0
    arcs_A: int = 0
    arcs_B: int = 0
    arcs_C: int = 0
    label_A: str = ""
    label_B: str = ""
    label_C: str = ""
    label_a: str = ""   # side label for side a (B–C)
    label_b: str = ""   # side label for side b (A–C)
    label_c: str = ""   # side label for side c (A–B)
    h: float = 0.0      # height (enables height-line mode)
    label_h: str = ""   # label for the height line
    name: str = ""
    pos: List[float] = field(default_factory=lambda: [0.0, 0.0])
    scale: float = 1.0


# ── Triangle solver ───────────────────────────────────────────────────────────

def _solve(given: dict) -> dict:
    """
    Solve the triangle from any valid combination of sides (a,b,c) and
    angles (A,B,C in degrees). Returns a completed dict with all six values.
    Raises ValueError for invalid, ambiguous (SSA), or under-specified inputs.
    """
    s = dict(given)

    def present(keys):
        return [k for k in keys if k in s]

    # Validate given angles
    for k in present('ABC'):
        if not (0 < s[k] < 180):
            raise ValueError(f"Angle {k} = {s[k]:.4g}° must be between 0° and 180°")

    ang_given = present('ABC')
    side_given = present('abc')
    na, ns = len(ang_given), len(side_given)

    # Three angles given: verify they sum to 180°
    if na == 3:
        total = s['A'] + s['B'] + s['C']
        if abs(total - 180) > 0.1:
            raise ValueError(f"Angles sum to {total:.4g}°, not 180°")

    # Two angles: check third would be positive
    if na == 2:
        derived = 180 - sum(s[k] for k in ang_given)
        if derived <= 0:
            raise ValueError(
                f"Given angles sum to {180 - derived:.4g}° — no room for third angle"
            )

    # Detect and reject SSA (two sides + non-included angle)
    if ns == 2 and na == 1:
        sk = frozenset(side_given)
        ak = ang_given[0]
        included = {
            frozenset('bc'): 'A',
            frozenset('ac'): 'B',
            frozenset('ab'): 'C',
        }
        if included.get(sk) != ak:
            raise ValueError(
                f"SSA ({', '.join(sorted(side_given))} with non-included angle {ak}) "
                f"is ambiguous — provide the included angle or all three sides instead"
            )

    # AA / AAA with no sides: add a canonical side so the solver can run
    if ns == 0:
        if na < 2:
            raise ValueError("Need at least 2 angles or a side + angle pair")
        # Derive missing angle if only 2 given
        if na == 2:
            missing_ang = present('ABC')  # the two we have
            m = [k for k in 'ABC' if k not in s][0]
            s[m] = 180 - s[ang_given[0]] - s[ang_given[1]]
        # Canonical scale: set c = 10; auto-zoom will fit it to the viewbox
        s['c'] = 10.0

    # Iterative solver: angle sum + law of sines + law of cosines
    for _ in range(20):
        ang_now = present('ABC')

        # Angle sum: fill the missing angle when two are known
        if len(ang_now) == 2:
            m = [k for k in 'ABC' if k not in s][0]
            val = 180 - s[ang_now[0]] - s[ang_now[1]]
            if val <= 0:
                raise ValueError("Angles must sum to 180° (derived angle came out ≤ 0)")
            s[m] = val

        # Law of sines: known side-angle pair → find other sides/angles
        pairs = [(k, k.upper()) for k in 'abc' if k in s and k.upper() in s]
        if pairs:
            sk, ak = pairs[0]
            ratio = s[sk] / math.sin(math.radians(s[ak]))
            for k in 'abc':
                K = k.upper()
                if K in s and k not in s:
                    s[k] = ratio * math.sin(math.radians(s[K]))
                elif k in s and K not in s:
                    sin_val = s[k] / ratio
                    if sin_val > 1.001:
                        raise ValueError(
                            f"No valid triangle: sin({K}) = {sin_val:.4f} > 1"
                        )
                    s[K] = math.degrees(math.asin(min(sin_val, 1.0)))

        # Law of cosines: a² = b² + c² − 2bc·cos(A), cyclically
        for s_opp, s1, s2, a_opp in [
            ('a', 'b', 'c', 'A'),
            ('b', 'a', 'c', 'B'),
            ('c', 'a', 'b', 'C'),
        ]:
            if s1 in s and s2 in s and a_opp in s and s_opp not in s:
                val = s[s1]**2 + s[s2]**2 - 2*s[s1]*s[s2]*math.cos(math.radians(s[a_opp]))
                s[s_opp] = math.sqrt(max(val, 0.0))
            elif s_opp in s and s1 in s and s2 in s and a_opp not in s:
                denom = 2 * s[s1] * s[s2]
                if denom > 0:
                    cos_val = (s[s1]**2 + s[s2]**2 - s[s_opp]**2) / denom
                    if -1 <= cos_val <= 1:
                        s[a_opp] = math.degrees(math.acos(cos_val))

        if all(k in s for k in 'abcABC'):
            break

    if not all(k in s for k in 'abc'):
        raise ValueError("Cannot determine triangle — check your parameters")

    return s


# ── Parse ─────────────────────────────────────────────────────────────────────

def parse(line: str) -> Optional[TriangleDiagram]:
    def get_num(key):
        m = re.search(rf'\b{key}:\s*(-?[\d.]+)', line)
        return float(m.group(1)) if m else None

    def get_int(key):
        v = get_num(key)
        # Also accept the singular form: arcs_A → arc_A
        if v is None and key.startswith("arcs_"):
            v = get_num("arc_" + key[5:])
        return int(v) if v is not None else None

    def get_str(key):
        # Double-quoted
        m = re.search(rf'\b{key}:\s*"([^"]*)"', line)
        if m:
            return m.group(1)
        # YAML-doubled single-quoted: ''value''
        m = re.search(rf"\b{key}:\s*''([^'']*)''", line)
        if m:
            return m.group(1)
        # Single-quoted
        m = re.search(rf"\b{key}:\s*'([^']*)'", line)
        if m:
            return m.group(1)
        # Unquoted — stop at , ) whitespace or quote
        m = re.search(rf'\b{key}:\s*([^,)\s"\']+)', line)
        return m.group(1) if m else ""

    pos_match = re.search(r'\bpos:\s*\(\s*(-?[\d.]+)\s*,\s*(-?[\d.]+)\s*\)', line)

    # Collect all given sides and angles
    given = {}
    for k in 'abc':
        v = get_num(k)
        if v is not None:
            given[k] = v
    for k in 'ABC':
        v = get_num(k)
        if v is not None:
            given[k] = v

    if not given:
        return None

    h_val = get_num("h")
    if h_val is not None:
        # Height mode: isoceles triangle with base a and height h.
        # Apex is placed at the midpoint of the base.
        a_val = given.get("a")
        if a_val is None:
            raise ValueError("Triangle: 'a' (base) is required when 'h' (height) is given")
        leg = math.sqrt((a_val / 2) ** 2 + h_val ** 2)
        solved = {"a": a_val, "b": leg, "c": leg}
    else:
        h_val = 0.0
        try:
            solved = _solve(given)
        except ValueError as e:
            raise ValueError(f"Triangle: {e}")

    a, b, c = solved['a'], solved['b'], solved['c']

    if a <= 0 or b <= 0 or c <= 0:
        raise ValueError("Triangle: all sides must be positive")
    if a + b <= c or a + c <= b or b + c <= a:
        raise ValueError(f"Triangle: sides {a:.4g}, {b:.4g}, {c:.4g} violate the triangle inequality")

    pos = [float(pos_match.group(1)), float(pos_match.group(2))] if pos_match else [0.0, 0.0]
    scale = get_num("scale") or 1.0

    # label_v: true  →  auto-label each side with its solved numeric value
    label_v_str = get_str("label_v")
    label_v = label_v_str.lower() in ("true", "1") if label_v_str else False

    # angle_labels: true  →  auto-label angles that were given by the user
    angle_labels_str = get_str("angle_labels")
    angle_labels = angle_labels_str.lower() in ("true", "1") if angle_labels_str else False

    # labels: "a, b, c"  →  shorthand for label_a/label_b/label_c
    labels_raw = get_str("labels")
    labels_list = [t.strip() for t in labels_raw.split(",")] if labels_raw else []

    def _side_label(key, idx, numeric):
        ind = get_str(key)
        if ind:
            return ind
        if idx < len(labels_list):
            return labels_list[idx]
        if label_v:
            v = float(numeric)
            return str(int(v)) if v == int(v) else str(round(v, 4))
        return ""

    def _angle_label(label_key, ang_key):
        """Manual label wins; otherwise auto-format the given angle if angle_labels: true."""
        ind = get_str(label_key)
        if ind:
            return ind
        if angle_labels and ang_key in given:
            v = given[ang_key]
            return (str(int(v)) + "°") if v == int(v) else f"{v:.4g}°"
        return ""

    label_h_val = get_str("label_h")

    return TriangleDiagram(
        a=a, b=b, c=c,
        ticks_a=get_int("ticks_a") or 0,
        ticks_b=get_int("ticks_b") or 0,
        ticks_c=get_int("ticks_c") or 0,
        arcs_A=get_int("arcs_A") or 0,
        arcs_B=get_int("arcs_B") or 0,
        arcs_C=get_int("arcs_C") or 0,
        label_A=_angle_label("label_A", "A"),
        label_B=_angle_label("label_B", "B"),
        label_C=_angle_label("label_C", "C"),
        label_a=_side_label("label_a", 0, a),
        label_b=_side_label("label_b", 1, b),
        label_c=_side_label("label_c", 2, c),
        h=h_val,
        label_h=label_h_val,
        name=get_str("name"),
        pos=pos,
        scale=scale,
    )


# ── Drawing helpers ───────────────────────────────────────────────────────────

def _tick_marks(x1, y1, x2, y2, count, sw, half=0.8, gap=0.44):
    if count <= 0:
        return ""

    mx = (x1 + x2) / 2
    my = (y1 + y2) / 2
    dx = x2 - x1
    dy = y2 - y1
    length = math.hypot(dx, dy)
    px = -dy / length
    py =  dx / length
    ux = dx / length
    uy = dy / length

    if count == 1:
        offsets = [0]
    elif count == 2:
        offsets = [-gap / 2, gap / 2]
    else:
        offsets = [-gap, 0, gap]

    parts = []
    for off in offsets:
        cx = mx + ux * off
        cy = my + uy * off
        parts.append(
            f'<line x1="{cx - px*half:.3f}" y1="{cy - py*half:.3f}" '
            f'x2="{cx + px*half:.3f}" y2="{cy + py*half:.3f}" '
            f'stroke="black" stroke-width="{sw}" stroke-linecap="round"/>'
        )
    return "\n".join(parts)


def _right_angle_marker(vx, vy, ang_to_a, ang_to_b, size, sw):
    """Small square at a vertex to indicate a 90° angle."""
    ux_a = math.cos(ang_to_a);  uy_a = -math.sin(ang_to_a)  # SVG dirs (y-inverted)
    ux_b = math.cos(ang_to_b);  uy_b = -math.sin(ang_to_b)
    p1x = vx + size * ux_a;  p1y = vy + size * uy_a
    p2x = vx + size * ux_b;  p2y = vy + size * uy_b
    p3x = p1x + size * ux_b; p3y = p1y + size * uy_b
    return (
        f'<path d="M{p1x:.3f},{p1y:.3f} L{p3x:.3f},{p3y:.3f} L{p2x:.3f},{p2y:.3f}" '
        f'fill="none" stroke="black" stroke-width="{sw:.3f}" '
        f'stroke-linejoin="miter" stroke-linecap="butt"/>'
    )


def _arc_indicators(cx, cy, angle_from, angle_to, count, sw, base_r=3.52, gap_r=0.72):
    if count <= 0:
        return ""

    BASE_R = base_r
    GAP_R  = gap_r

    a1 = angle_from
    a2 = angle_to
    while a2 < a1:
        a2 += 2 * math.pi
    sweep = a2 - a1
    large_arc = 1 if sweep > math.pi else 0

    parts = []
    for i in range(count):
        r = BASE_R + i * GAP_R
        sx1 = cx + r * math.cos(a1)
        sy1 = cy - r * math.sin(a1)
        sx2 = cx + r * math.cos(a2)
        sy2 = cy - r * math.sin(a2)
        parts.append(
            f'<path d="M{sx1:.3f},{sy1:.3f} A{r},{r} 0 {large_arc},0 {sx2:.3f},{sy2:.3f}" '
            f'fill="none" stroke="black" stroke-width="{sw * 0.7:.2f}"/>'
        )
    return "\n".join(parts)


def _angle_label(vx, vy, cent_svgx, cent_svgy, text, font_size, min_label_r=0.0):
    """Label placed toward the SVG centroid, guaranteed beyond min_label_r from vertex."""
    if not text:
        return ""
    dx = cent_svgx - vx
    dy = cent_svgy - vy
    dist = math.hypot(dx, dy)
    if dist == 0:
        return ""
    ux, uy = dx / dist, dy / dist
    label_r = max(dist * 0.44, min_label_r + font_size)
    lx = vx + ux * label_r
    ly = vy + uy * label_r
    return (
        f'<text x="{lx:.3f}" y="{ly:.3f}" '
        f'font-size="{font_size}" font-family="system-ui, -apple-system, sans-serif" '
        f'text-anchor="middle" dominant-baseline="middle">'
        f'{text}</text>'
    )


def _side_label(x1, y1, x2, y2, opp_x, opp_y, text, font_size, offset=None):
    """Label placed at the midpoint of a side, offset outward (away from opposite vertex)."""
    if not text:
        return ""
    mx = (x1 + x2) / 2
    my = (y1 + y2) / 2
    dx = x2 - x1
    dy = y2 - y1
    length = math.hypot(dx, dy)
    if length == 0:
        return ""
    px, py = -dy / length, dx / length
    to_opp_x = opp_x - mx
    to_opp_y = opp_y - my
    if px * to_opp_x + py * to_opp_y > 0:
        px, py = -px, -py
    if offset is None:
        offset = font_size * 1.1
    lx = mx + px * offset
    ly = my + py * offset
    # For near-vertical sides the label is offset horizontally; centering the text
    # would push half of it back into the triangle.  Anchor to the near edge instead.
    if px > 0.5:
        anchor = "start"   # label is to the right — text extends further right
    elif px < -0.5:
        anchor = "end"     # label is to the left  — text extends further left
    else:
        anchor = "middle"
    return (
        f'<text x="{lx:.3f}" y="{ly:.3f}" '
        f'font-size="{font_size}" font-family="system-ui, -apple-system, sans-serif" '
        f'text-anchor="{anchor}" dominant-baseline="middle">'
        f'{text}</text>'
    )


# ── Render ────────────────────────────────────────────────────────────────────

def render(d: TriangleDiagram, viz_scale: float = None) -> str:
    a, b, c = d.a, d.b, d.c
    cx0, cy0 = d.pos
    scale = d.scale

    # Place B at origin, C along +x; compute A via law of cosines
    bx, by = 0.0, 0.0
    cx, cy = a, 0.0
    cos_b = (a*a + c*c - b*b) / (2*a*c)
    ax = c * cos_b
    ay = c * math.sqrt(max(0.0, 1 - cos_b*cos_b))

    # Centroid
    cent_x = (ax + bx + cx) / 3
    cent_y = (ay + by + cy) / 3

    def to_svg(x, y):
        return (
            cx0 + (x - cent_x) * scale,
            cy0 - (y - cent_y) * scale,
        )

    sax, say = to_svg(ax, ay)
    sbx, sby = to_svg(bx, by)
    scx, scy = to_svg(cx, cy)
    s_cent_x, s_cent_y = to_svg(cent_x, cent_y)

    # viz_scale controls font/stroke/tick sizes independently of geometry.
    # When called from the engine (multi-diagram), the engine passes a global
    # viz_scale computed from the combined bbox of all diagrams.
    # When called standalone (viz_scale=None), estimate from own content.
    if viz_scale is None:
        content_w = max(sax, sbx, scx) - min(sax, sbx, scx)
        content_h = max(say, sby, scy) - min(say, sby, scy)
        content_span = max(content_w, content_h * (60.0 / 36.0))  # 5:3 aspect ratio
        expected_vw = content_span / 0.92   # approx post-zoom viewBox width
        viz_scale = expected_vw / 60.0

    sw           = 0.192 * viz_scale
    font_size    = 2.0   * viz_scale
    label_offset = 2.2   * viz_scale  # font_size * 1.1
    tick_half    = 0.8   * viz_scale
    tick_gap     = 0.44  * viz_scale
    arc_base     = 3.52  * viz_scale
    arc_gap      = 0.72  * viz_scale
    ra_size      = 2.0   * viz_scale  # right-angle square marker
    out = []

    # Per-vertex arc radius: 25% of shorter adjacent side, capped at a fixed SVG-unit
    # maximum so arcs don't become oversized on large triangles.  The cap is NOT
    # multiplied by viz_scale so arcs scale with the triangle geometry rather than
    # the viewBox zoom level.  The gap ratio is constant (arc_gap/arc_base = 0.72/3.52).
    svg_a = math.hypot(scx - sbx, scy - sby)
    svg_b = math.hypot(scx - sax, scy - say)
    svg_c = math.hypot(sbx - sax, sby - say)
    _arc_max   = 3.52                   # fixed SVG-unit cap
    _gap_ratio = 0.72 / 3.52            # arc_gap / arc_base — constant

    def _vert_arc(shorter_side: float):
        r = min(_arc_max, 0.25 * shorter_side)
        return r, r * _gap_ratio

    arc_r_A, arc_g_A = _vert_arc(min(svg_b, svg_c))
    arc_r_B, arc_g_B = _vert_arc(min(svg_a, svg_c))
    arc_r_C, arc_g_C = _vert_arc(min(svg_a, svg_b))

    # Sides
    out.append(f'<line x1="{sbx:.3f}" y1="{sby:.3f}" x2="{scx:.3f}" y2="{scy:.3f}" stroke="black" stroke-width="{sw}" stroke-linecap="round"/>')
    out.append(f'<line x1="{sax:.3f}" y1="{say:.3f}" x2="{scx:.3f}" y2="{scy:.3f}" stroke="black" stroke-width="{sw}" stroke-linecap="round"/>')
    out.append(f'<line x1="{sax:.3f}" y1="{say:.3f}" x2="{sbx:.3f}" y2="{sby:.3f}" stroke="black" stroke-width="{sw}" stroke-linecap="round"/>')

    # Tick marks: side a (B–C), side b (A–C), side c (A–B)
    out.append(_tick_marks(sbx, sby, scx, scy, d.ticks_a, sw * 0.8, tick_half, tick_gap))
    out.append(_tick_marks(sax, say, scx, scy, d.ticks_b, sw * 0.8, tick_half, tick_gap))
    out.append(_tick_marks(sax, say, sbx, sby, d.ticks_c, sw * 0.8, tick_half, tick_gap))

    # Side length labels — suppressed in pass 1 (viz_scale == 1.0) to avoid inflating the bbox
    if viz_scale != 1.0:
        out.append(_side_label(sbx, sby, scx, scy, sax, say, d.label_a, font_size, label_offset))  # side a, opp A
        out.append(_side_label(sax, say, scx, scy, sbx, sby, d.label_b, font_size, label_offset))  # side b, opp B
        out.append(_side_label(sax, say, sbx, sby, scx, scy, d.label_c, font_size, label_offset))  # side c, opp C

    # Height line (only in height mode: h > 0)
    if d.h > 0:
        # Foot of the perpendicular: directly below apex A on the base
        s_foot_x, s_foot_y = to_svg(ax, 0.0)
        dash = f"{sw * 3:.2f},{sw * 2:.2f}"
        out.append(
            f'<line x1="{sax:.3f}" y1="{say:.3f}" x2="{s_foot_x:.3f}" y2="{s_foot_y:.3f}" '
            f'stroke="black" stroke-width="{sw}" stroke-dasharray="{dash}" stroke-linecap="round"/>'
        )
        # Right-angle marker at the foot (up toward apex, right toward C)
        out.append(_right_angle_marker(s_foot_x, s_foot_y, math.pi / 2, 0.0, ra_size, sw))
        # Label at the midpoint of the height line, offset to the right
        if d.label_h and viz_scale != 1.0:
            lx = sax + font_size * 1.2
            ly = s_foot_y + 0.3 * (say - s_foot_y)
            out.append(
                f'<text x="{lx:.3f}" y="{ly:.3f}" '
                f'font-size="{font_size}" font-family="system-ui, -apple-system, sans-serif" '
                f'text-anchor="middle" dominant-baseline="middle">'
                f'{d.label_h}</text>'
            )

    # Angle arcs and labels
    def math_angle(from_x, from_y, to_x, to_y):
        return math.atan2(-(to_y - from_y), to_x - from_x)

    def short_arc(p, q):
        sweep = (q - p) % (2 * math.pi)
        return (p, q) if sweep <= math.pi else (q, p)

    ang_atob = math_angle(sax, say, sbx, sby)
    ang_atoc = math_angle(sax, say, scx, scy)
    out.append(_arc_indicators(sax, say, *short_arc(ang_atob, ang_atoc), d.arcs_A, sw * 0.8, arc_r_A, arc_g_A))
    if viz_scale != 1.0:
        outer_r_A = (arc_r_A + (d.arcs_A - 1) * arc_g_A) if d.arcs_A > 0 else 0.0
        out.append(_angle_label(sax, say, s_cent_x, s_cent_y, d.label_A, font_size, outer_r_A))

    ang_btoa = math_angle(sbx, sby, sax, say)
    ang_btoc = math_angle(sbx, sby, scx, scy)
    out.append(_arc_indicators(sbx, sby, *short_arc(ang_btoa, ang_btoc), d.arcs_B, sw * 0.8, arc_r_B, arc_g_B))
    if viz_scale != 1.0:
        outer_r_B = (arc_r_B + (d.arcs_B - 1) * arc_g_B) if d.arcs_B > 0 else 0.0
        out.append(_angle_label(sbx, sby, s_cent_x, s_cent_y, d.label_B, font_size, outer_r_B))

    ang_ctoa = math_angle(scx, scy, sax, say)
    ang_ctob = math_angle(scx, scy, sbx, sby)
    cos_C = (a*a + b*b - c*c) / (2*a*b)
    if abs(cos_C) < 0.01:  # right angle at C — draw square marker
        out.append(_right_angle_marker(scx, scy, ang_ctoa, ang_ctob, ra_size, sw))
    else:
        out.append(_arc_indicators(scx, scy, *short_arc(ang_ctoa, ang_ctob), d.arcs_C, sw * 0.8, arc_r_C, arc_g_C))
    if viz_scale != 1.0:
        outer_r_C = (arc_r_C + (d.arcs_C - 1) * arc_g_C) if d.arcs_C > 0 else 0.0
        out.append(_angle_label(scx, scy, s_cent_x, s_cent_y, d.label_C, font_size, outer_r_C))

    if d.name and viz_scale != 1.0:
        out.append(
            f'<text x="{s_cent_x:.3f}" y="{s_cent_y + font_size * 0.35:.3f}" text-anchor="middle" '
            f'font-size="{font_size}" font-family="system-ui, -apple-system, sans-serif" fill="#333">{d.name}</text>'
        )

    return "\n".join(p for p in out if p)
