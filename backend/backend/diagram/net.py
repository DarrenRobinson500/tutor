import re
import math
from dataclasses import dataclass, field
from typing import List, Optional, Tuple

DIAGRAM_TYPE = "Net"
SUPPORTS_VIZ_SCALE = True

# Syntax:
#   Net(shape: rect_prism, width: 4, height: 3, depth: 2)
#   Net(shape: cylinder, radius: 3, height: 5)
#   Net(shape: cone, radius: 3, slant: 5)          [slant=0 → computed from radius+height]
#   Net(shape: rect_pyramid, width: 4, depth: 4, height: 3)
#   Net(shape: tri_prism, a: 3, b: 4, c: 5, depth: 6)
#   Net(shape: tri_pyramid, a: 5)                  [equilateral tetrahedron, side a]
#
# labels: true (default) — show dimension labels on the net
#
# show: <comma-separated part names> — show only the listed parts (default: all)
#
# Part names per shape:
#   cylinder:     rect, top, bottom
#   cone:         sector, base
#   rect_prism:   top, front, bottom, left, right, back
#   rect_pyramid: base, front, back, left, right
#   tri_prism:    rect_a, rect_b, rect_c, tri_top, tri_bottom
#   tri_pyramid:  base, face_a, face_b, face_c


@dataclass
class NetDiagram:
    shape: str = "rect_prism"
    width: float = 4.0
    height: float = 3.0
    depth: float = 2.0
    radius: float = 3.0
    slant: float = 0.0
    a: float = 3.0
    b: float = 4.0
    c: float = 5.0
    labels: bool = True
    show: List[str] = field(default_factory=list)


def parse(line: str) -> Optional[NetDiagram]:
    def get_str(key, default=""):
        m = re.search(rf'\b{key}:\s*"([^"]*)"', line)
        if m:
            return m.group(1)
        m = re.search(rf'\b{key}:\s*([^,)\s]+)', line)
        return m.group(1) if m else default

    def get_num(key, default):
        m = re.search(rf'\b{key}:\s*([\d.]+)', line)
        return float(m.group(1)) if m else default

    shape = get_str("shape", "rect_prism")
    valid = {"rect_prism", "cone", "cylinder", "rect_pyramid", "tri_prism", "tri_pyramid"}
    if shape not in valid:
        return None

    labels_m = re.search(r'\blabels:\s*(true|false)', line)
    labels = (labels_m.group(1) != 'false') if labels_m else True

    show: List[str] = []
    sm = re.search(r'\bshow:\s*"([^"]*)"', line)
    if sm:
        show = [p.strip() for p in sm.group(1).split(',') if p.strip()]
    else:
        sm = re.search(r'\bshow:\s*([^)]+)', line)
        if sm:
            show = [p.strip() for p in sm.group(1).split(',') if p.strip()]

    return NetDiagram(
        shape=shape,
        width=get_num("width", 4.0),
        height=get_num("height", 3.0),
        depth=get_num("depth", 2.0),
        radius=get_num("radius", 3.0),
        slant=get_num("slant", 0.0),
        a=get_num("a", 3.0),
        b=get_num("b", 4.0),
        c=get_num("c", 5.0),
        labels=labels,
        show=show,
    )


# ── Base constants (at viz_scale = 1.0, viewBox width = 60) ──────────────────

_SW   = 0.16   # stroke width
_FS   = 2.0    # label font size
_FILL = "#f4f4f4"
_FILL_ACCENT = "#e0eeff"

Tagged = List[Tuple[str, str]]


# ── SVG helpers (accept scaled sw / fs) ──────────────────────────────────────

def _r(x, y, w, h, fill=_FILL, sw=_SW):
    return (f'<rect x="{x:.3f}" y="{y:.3f}" width="{w:.3f}" height="{h:.3f}" '
            f'fill="{fill}" stroke="black" stroke-width="{sw:.3f}"/>')


def _p(pts, fill=_FILL, sw=_SW):
    s = " ".join(f"{x:.3f},{y:.3f}" for x, y in pts)
    return (f'<polygon points="{s}" fill="{fill}" '
            f'stroke="black" stroke-width="{sw:.3f}" stroke-linejoin="round"/>')


def _circ(cx, cy, radius, fill=_FILL, sw=_SW):
    return (f'<circle cx="{cx:.3f}" cy="{cy:.3f}" r="{radius:.3f}" '
            f'fill="{fill}" stroke="black" stroke-width="{sw:.3f}"/>')


def _t(x, y, text, fs=_FS):
    return (f'<text x="{x:.3f}" y="{y:.3f}" font-size="{fs:.3f}" '
            f'font-family="system-ui, -apple-system, sans-serif" fill="#333" '
            f'text-anchor="middle" dominant-baseline="middle">'
            f'{text}</text>')


def _fmt(n):
    return str(int(n)) if n == int(n) else f"{n:g}"


def _tri_verts(a, b, c):
    cos_b = max(-1.0, min(1.0, (a*a + c*c - b*b) / (2*a*c)))
    ax = c * cos_b
    ay = c * math.sqrt(max(0.0, 1 - cos_b*cos_b))
    return (ax, ay), (0.0, 0.0), (a, 0.0)


# ── Shape nets ───────────────────────────────────────────────────────────────

def _net_rect_prism(d: NetDiagram, sw: float, fs: float) -> Tagged:
    w, h, dep = d.width, d.height, d.depth
    scale = 20.0 / max(2*(dep + w), 2*dep + h, 0.1)
    W, H, D = w*scale, h*scale, dep*scale
    net_w = 2*D + 2*W
    net_h = 2*D + H
    ox, oy = -net_w/2, -net_h/2

    out: Tagged = [
        ("top",    _r(ox + D,         oy,         W, D, _FILL_ACCENT, sw)),
        ("front",  _r(ox + D,         oy + D,     W, H, _FILL,        sw)),
        ("bottom", _r(ox + D,         oy + D + H, W, D, _FILL_ACCENT, sw)),
        ("left",   _r(ox,             oy + D,     D, H, _FILL,        sw)),
        ("right",  _r(ox + D + W,     oy + D,     D, H, _FILL,        sw)),
        ("back",   _r(ox + 2*D + W,   oy + D,     W, H, _FILL,        sw)),
    ]

    if d.labels:
        fw, fh, fd = _fmt(w), _fmt(h), _fmt(dep)
        lp = fs * 1.0
        lp_close = lp * 0.8
        out.append(("bottom", _t(ox + D + W/2,      oy + 2*D + H + lp, fw, fs)))
        out.append(("left",   _t(ox - lp_close,      oy + D + H/2,      fh, fs)))
        out.append(("top",    _t(ox + D - lp_close,  oy + D/2,          fd, fs)))

    return out


def _net_cylinder(d: NetDiagram, sw: float, fs: float) -> Tagged:
    r, h = d.radius, d.height
    circ = 2 * math.pi * r
    scale = 20.0 / max(circ, 2*r + h, 0.1)
    R = r * scale
    H = h * scale
    C = circ * scale

    out: Tagged = [
        ("rect",   _r(-C/2, -H/2, C, H, _FILL,        sw)),
        ("top",    _circ(0, -H/2 - R, R, _FILL_ACCENT, sw)),
        ("bottom", _circ(0,  H/2 + R, R, _FILL_ACCENT, sw)),
    ]

    if d.labels:
        lp = fs * 1.0
        bcy = H/2 + R
        out.append(("rect",   _t(-C/2 - lp, 0, _fmt(h), fs)))
        out.append(("bottom",
            f'<line x1="0" y1="{bcy:.3f}" x2="{R:.3f}" y2="{bcy:.3f}" '
            f'stroke="#888" stroke-width="{sw*1.5:.3f}"/>'))
        out.append(("bottom", _t(R/2, bcy - fs * 0.7, _fmt(r), fs)))

    return out


def _net_cone(d: NetDiagram, sw: float, fs: float) -> Tagged:
    r = d.radius
    h = d.height
    slant = d.slant if d.slant > 0 else math.sqrt(r*r + h*h)
    theta = min(2 * math.pi * r / slant, 2*math.pi * 0.98)

    scale = 10.0 / max(slant + r + 1, 0.1)
    L = slant * scale
    R = r * scale

    half = theta / 2
    arc_ex = L * math.sin(half)
    arc_ey = L * math.cos(half)
    arc_bot = L
    cc_raw = arc_bot + R
    y_min = min(0.0, arc_ey)
    y_max = max(arc_bot, cc_raw + R)
    shift_y = (y_min + y_max) / 2

    apex_y = -shift_y
    aey    = arc_ey - shift_y
    bot_y  = arc_bot - shift_y
    cc     = cc_raw - shift_y

    large = 1 if theta > math.pi else 0
    sweep = 0  # always counter-clockwise so the arc curves through the bottom toward the base circle
    sector = (f'<path d="M0,{apex_y:.3f} L{-arc_ex:.3f},{aey:.3f} '
              f'A{L:.3f},{L:.3f} 0 {large},{sweep} {arc_ex:.3f},{aey:.3f} Z" '
              f'fill="{_FILL}" stroke="black" stroke-width="{sw:.3f}" stroke-linejoin="round"/>')
    bot_anchor = f'<line x1="0" y1="{bot_y:.3f}" x2="0.001" y2="{bot_y:.3f}" stroke="none"/>'

    out: Tagged = [
        ("sector", sector),
        ("sector", bot_anchor),
        ("base",   _circ(0, cc, R, _FILL_ACCENT, sw)),
    ]

    if d.labels:
        lp = fs * 1.0
        out.append(("sector", _t(arc_ex / 2 + lp, (apex_y + aey) / 2, _fmt(slant), fs)))
        out.append(("base",   _t(0, cc + R + lp, _fmt(r), fs)))

    return out


def _net_rect_pyramid(d: NetDiagram, sw: float, fs: float) -> Tagged:
    w, dep, h = d.width, d.depth, d.height
    sf = math.sqrt(h*h + (dep/2)**2)
    sl = math.sqrt(h*h + (w/2)**2)
    scale = 20.0 / max(w + 2*sl, dep + 2*sf, 0.1)
    W, D = w*scale, dep*scale
    SF, SL = sf*scale, sl*scale

    # Dotted height line on right face: midpoint of base edge → apex
    _tick = sw * 3.5
    _right_height_line = (
        f'<line x1="{W/2:.3f}" y1="0.000" x2="{W/2 + SL:.3f}" y2="0.000" '
        f'stroke="#555" stroke-width="{sw:.3f}" '
        f'stroke-dasharray="{sw*4:.3f} {sw*2.5:.3f}"/>'
    )
    _right_angle_mark = (
        f'<polyline points="{W/2:.3f},{-_tick:.3f} {W/2+_tick:.3f},{-_tick:.3f} {W/2+_tick:.3f},0.000" '
        f'fill="none" stroke="#555" stroke-width="{sw:.3f}"/>'
    )

    out: Tagged = [
        ("base",  _r(-W/2, -D/2, W, D, _FILL_ACCENT, sw)),
        ("front", _p([(-W/2, D/2),  (W/2, D/2),  (0, D/2 + SF)],          _FILL, sw)),
        ("back",  _p([(-W/2, -D/2), (W/2, -D/2), (0, -D/2 - SF)],         _FILL, sw)),
        ("left",  _p([(-W/2, -D/2), (-W/2, D/2), (-W/2 - SL, 0)],         _FILL, sw)),
        ("right", _p([(W/2,  -D/2), (W/2,  D/2), (W/2 + SL, 0)],          _FILL, sw)),
        ("right", _right_height_line),
        ("right", _right_angle_mark),
    ]

    if d.labels:
        lp = fs * 1.0
        lp_close = lp * 0.8
        out.append(("base",  _t(0, D/2 + lp_close, _fmt(w), fs)))
        out.append(("base",  _t(-W/2 - lp_close, 0, _fmt(dep), fs)))
        el = math.hypot(SL, D / 2)
        if el > 0:
            opx, opy = (D / 2) / el, SL / el
            mx, my = W / 2 + SL / 2, D / 4
            out.append(("right", _t(mx + opx * lp, my + opy * lp, _fmt(h), fs)))

    return out


def _net_tri_prism(d: NetDiagram, sw: float, fs: float) -> Tagged:
    a, b, c, dep = d.a, d.b, d.c, d.depth
    (ax, ay), _, _ = _tri_verts(a, b, c)
    total_rect_w = a + b + c
    scale = 20.0 / max(total_rect_w, dep + 2*ay, 0.1)
    A, B, C2 = a*scale, b*scale, c*scale
    D = dep*scale
    AX, AY = ax*scale, ay*scale

    net_w = A + B + C2
    ox = -net_w / 2
    oy = -(D + AY) / 2 + AY

    out: Tagged = [
        ("rect_a",     _r(ox,         oy, A,  D, _FILL, sw)),
        ("rect_b",     _r(ox + A,     oy, B,  D, _FILL, sw)),
        ("rect_c",     _r(ox + A + B, oy, C2, D, _FILL, sw)),
        ("tri_top",    _p([(ox, oy),     (ox + A, oy),     (ox + AX, oy - AY)],     _FILL_ACCENT, sw)),
        ("tri_bottom", _p([(ox, oy + D), (ox + A, oy + D), (ox + AX, oy + D + AY)], _FILL_ACCENT, sw)),
    ]

    if d.labels:
        lp = fs * 1.0
        lbl_y = oy + D - fs * 0.45
        out.append(("rect_a", _t(ox + A/2,          lbl_y, _fmt(a), fs)))
        out.append(("rect_b", _t(ox + A + B/2,      lbl_y, _fmt(b), fs)))
        out.append(("rect_c", _t(ox + A + B + C2/2, lbl_y, _fmt(c), fs)))
        out.append(("rect_a", _t(ox - lp * 0.7, oy + D/2, _fmt(dep), fs)))

    return out


def _net_tri_pyramid(d: NetDiagram, sw: float, fs: float) -> Tagged:
    a = d.a
    h = a * math.sqrt(3) / 2
    scale = 18.0 / max(2*a, 2*h, 0.1)
    A = a * scale
    H = h * scale
    bx = A / 2

    def sv(pts):
        return [(x - bx, y) for x, y in pts]

    T0 = sv([(0, 0),   (A, 0),   (A/2,  H)])
    T1 = sv([(0, 0),   (A, 0),   (A/2, -H)])
    T2 = sv([(A, 0),   (A/2, H), (3*A/2, H)])
    T3 = sv([(A/2, H), (0, 0),   (-A/2,  H)])

    out: Tagged = [
        ("base",   _p(T0, _FILL_ACCENT, sw)),
        ("face_a", _p(T1, _FILL,        sw)),
        ("face_b", _p(T2, _FILL,        sw)),
        ("face_c", _p(T3, _FILL,        sw)),
    ]

    if d.labels:
        lp = fs * 1.0
        t0_bottom = T0[2]
        out.append(("base", _t(t0_bottom[0], t0_bottom[1] + lp, _fmt(a), fs)))

    return out


# ── Main render entry point ───────────────────────────────────────────────────

def render(d: NetDiagram, viz_scale: float = 1.0) -> str:
    # Scale stroke width and font size so they appear constant in screen pixels
    # regardless of how much the auto-zoom shrinks or expands the viewBox.
    sw = _SW * viz_scale
    fs = _FS * viz_scale

    dispatch = {
        "rect_prism":   _net_rect_prism,
        "cylinder":     _net_cylinder,
        "cone":         _net_cone,
        "rect_pyramid": _net_rect_pyramid,
        "tri_prism":    _net_tri_prism,
        "tri_pyramid":  _net_tri_pyramid,
    }
    fn = dispatch.get(d.shape)
    if fn is None:
        return ""

    # Labels are suppressed on pass 1 (viz_scale == 1.0) so their text bbox
    # doesn't inflate the content bbox used by the auto-zoom calculation.
    labels_on = d.labels and viz_scale != 1.0
    d_pass = NetDiagram(
        shape=d.shape, width=d.width, height=d.height, depth=d.depth,
        radius=d.radius, slant=d.slant, a=d.a, b=d.b, c=d.c,
        labels=labels_on, show=d.show,
    )

    tagged = fn(d_pass, sw, fs)

    if d.show:
        allowed = set(d.show)
        elements = [svg for tag, svg in tagged if tag in allowed]
    else:
        elements = [svg for _, svg in tagged]

    return "\n".join(e for e in elements if e)
