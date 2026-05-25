import re
import math
import ast
import operator
from dataclasses import dataclass, field
from typing import List, Optional, Tuple

DIAGRAM_TYPE = "ScatterPlot"
SUPPORTS_VIZ_SCALE = True

_FONT = "system-ui, -apple-system, sans-serif"

_C_AXIS    = "#334155"
_C_GRID    = "#e2e8f0"
_C_POINT   = "#2563eb"
_C_LINE    = "#dc2626"
_C_TREND   = "#94a3b8"
_C_PREDICT = "#ea580c"
_C_GRAD    = "#7c3aed"
_C_INTCPT  = "#16a34a"
_C_HL      = "#f59e0b"

# Viewbox: 60 × 50 SVG units (≈ 460:380 aspect ratio)
_VB_W = 60.0
_VB_H = 50.0

# Plot area insets
_INS_L = 9.0
_INS_R = 3.0
_INS_T = 4.0
_INS_B = 8.0

_PX0 = _INS_L
_PY0 = _INS_T
_PX1 = _VB_W - _INS_R
_PY1 = _VB_H - _INS_B
_PW  = _PX1 - _PX0
_PH  = _PY1 - _PY0


@dataclass
class ScatterPlotDiagram:
    points:               List[Tuple[float, float]]
    x_label:              str
    y_label:              str
    title:                Optional[str]              = None
    equation:             Optional[str]              = None
    show_line:            bool                       = True
    show_trend:           bool                       = False
    predict_x:            Optional[float]            = None
    gradient_annotation:  bool                       = False
    intercept_annotation: bool                       = False
    highlight:            List[Tuple[float, float]]  = field(default_factory=list)
    x_min:                Optional[float]            = None
    x_max:                Optional[float]            = None
    y_min:                Optional[float]            = None
    y_max:                Optional[float]            = None


# ── Safe expression evaluator ─────────────────────────────────────────────────

_AST_OPS = {
    ast.Add:  operator.add,
    ast.Sub:  operator.sub,
    ast.Mult: operator.mul,
    ast.Div:  operator.truediv,
    ast.Pow:  operator.pow,
    ast.USub: operator.neg,
    ast.UAdd: operator.pos,
}


def _safe_eval(expr: str, x: float) -> Optional[float]:
    try:
        tree = ast.parse(expr.replace('^', '**'), mode='eval')

        def _ev(node):
            if isinstance(node, ast.Expression):
                return _ev(node.body)
            if isinstance(node, ast.Constant):
                return float(node.value)
            if isinstance(node, ast.Name) and node.id == 'x':
                return x
            if isinstance(node, ast.BinOp):
                return _AST_OPS[type(node.op)](_ev(node.left), _ev(node.right))
            if isinstance(node, ast.UnaryOp):
                return _AST_OPS[type(node.op)](_ev(node.operand))
            raise ValueError(f"Unsupported: {ast.dump(node)}")

        return _ev(tree)
    except Exception:
        return None


# ── Stats helpers ─────────────────────────────────────────────────────────────

def _least_squares(points):
    n = len(points)
    if n < 2:
        return None, None
    sx  = sum(p[0] for p in points)
    sy  = sum(p[1] for p in points)
    sxy = sum(p[0] * p[1] for p in points)
    sxx = sum(p[0] * p[0] for p in points)
    denom = n * sxx - sx * sx
    if abs(denom) < 1e-12:
        return None, None
    m = (n * sxy - sx * sy) / denom
    b = (sy - m * sx) / n
    return m, b


def _nice_ticks(lo: float, hi: float, target: int = 5) -> List[float]:
    span = hi - lo
    if span <= 0:
        return [lo]
    raw_step = span / target
    mag = 10 ** math.floor(math.log10(raw_step))
    nice = [1, 2, 2.5, 5, 10]
    step = mag * min(nice, key=lambda s: abs(s * mag - raw_step))
    start = math.ceil(lo / step) * step
    ticks: List[float] = []
    v = start
    while v <= hi + step * 0.01:
        ticks.append(round(v, 10))
        v += step
    return ticks


def _fmt(v: float) -> str:
    if v == int(v):
        return str(int(v))
    return f"{v:.4g}"


# ── Parsing ───────────────────────────────────────────────────────────────────

def _parse_pairs(text: str) -> List[Tuple[float, float]]:
    """Parse numeric pairs from text, accepting both (x,y) and [x,y] notation."""
    pairs = []
    for m in re.finditer(r'[\(\[]\s*(-?[\d.]+)\s*,\s*(-?[\d.]+)\s*[\)\]]', text):
        pairs.append((float(m.group(1)), float(m.group(2))))
    return pairs


def _extract_value_region(line: str, key: str) -> str:
    """Return the text after `key:` up to (but not including) the next parameter key.

    Tracks bracket depth so commas inside [x,y] pairs don't trigger a stop.
    Stops at `, word:` at depth 0 (next parameter) or an unmatched closing bracket.
    """
    m = re.search(rf'\b{key}:\s*', line)
    if not m:
        return ''
    pos      = m.end()
    depth    = 0
    in_quote = False
    qchar    = ''
    while pos < len(line):
        ch = line[pos]
        if in_quote:
            if ch == qchar:
                in_quote = False
        elif ch in ('"', "'"):
            in_quote = True
            qchar    = ch
        elif ch in '([':
            depth += 1
        elif ch in ')]':
            if depth > 0:
                depth -= 1
            else:
                break  # hit the outer closing bracket
        elif depth == 0 and ch == ',':
            if re.match(r',\s*\w+\s*:', line[pos:]):
                break  # next parameter key starts here
        pos += 1
    return line[m.end():pos]


def _extract_str(line: str, key: str) -> Optional[str]:
    m = re.search(rf'\b{key}:\s*"([^"]*)"', line)
    if m:
        return m.group(1)
    m = re.search(rf"\b{key}:\s*'([^']*)'", line)
    if m:
        return m.group(1)
    return None


def parse(line: str) -> Optional[ScatterPlotDiagram]:
    if 'points:' not in line:
        return None
    points = _parse_pairs(_extract_value_region(line, 'points'))
    if not points:
        return None

    x_label  = _extract_str(line, 'x_label') or ''
    y_label  = _extract_str(line, 'y_label') or ''
    title    = _extract_str(line, 'title')
    equation = _extract_str(line, 'equation')

    def _bool(key, default):
        m = re.search(rf'\b{key}:\s*(true|false)', line)
        return (m.group(1) == 'true') if m else default

    def _num(key):
        m = re.search(rf'\b{key}:\s*(-?[\d.]+)', line)
        return float(m.group(1)) if m else None

    highlight = _parse_pairs(_extract_value_region(line, 'highlight'))

    return ScatterPlotDiagram(
        points               = points,
        x_label              = x_label,
        y_label              = y_label,
        title                = title,
        equation             = equation,
        show_line            = _bool('show_line', True),
        show_trend           = _bool('show_trend', False),
        predict_x            = _num('predict_x'),
        gradient_annotation  = _bool('gradient_annotation', False),
        intercept_annotation = _bool('intercept_annotation', False),
        highlight            = highlight,
        x_min                = _num('x_min'),
        x_max                = _num('x_max'),
        y_min                = _num('y_min'),
        y_max                = _num('y_max'),
    )


# ── Engine interface ──────────────────────────────────────────────────────────

def viewbox(d: ScatterPlotDiagram) -> tuple:
    return (0.0, 0.0, _VB_W, _VB_H)


def render(d: ScatterPlotDiagram, viz_scale: float = 1.0) -> str:
    # ── Axis ranges ───────────────────────────────────────────────────────────
    xs = [p[0] for p in d.points]
    ys = [p[1] for p in d.points]

    def _auto(vals, margin=0.1):
        lo, hi = min(vals), max(vals)
        span = hi - lo or 1.0
        return lo - span * margin, hi + span * margin

    x_min = d.x_min if d.x_min is not None else _auto(xs)[0]
    x_max = d.x_max if d.x_max is not None else _auto(xs)[1]
    y_min = d.y_min if d.y_min is not None else _auto(ys)[0]
    y_max = d.y_max if d.y_max is not None else _auto(ys)[1]

    x_range = x_max - x_min or 1.0
    y_range = y_max - y_min or 1.0

    def sx(x): return _PX0 + (x - x_min) / x_range * _PW
    def sy(y): return _PY1 - (y - y_min) / y_range * _PH

    x_ticks = _nice_ticks(x_min, x_max, 5)
    y_ticks = _nice_ticks(y_min, y_max, 5)

    slope, intercept = _least_squares(d.points)

    _line_y = None
    if d.equation:
        _eq = d.equation
        _line_y = lambda x: _safe_eval(_eq, x)
    elif slope is not None:
        _m, _b = slope, intercept
        _line_y = lambda x: _m * x + _b

    sw       = 0.25  * viz_scale
    fs_tick  = 1.6   * viz_scale
    fs_label = 2.0   * viz_scale
    fs_title = 2.2   * viz_scale
    fs_pt    = 1.5   * viz_scale
    dot_r    = 0.9   * viz_scale
    hl_r     = 1.2   * viz_scale
    tick_len = 0.9   * viz_scale

    out = []

    # ── Plot background ───────────────────────────────────────────────────────
    out.append(
        f'<rect x="{_PX0:.3f}" y="{_PY0:.3f}" width="{_PW:.3f}" height="{_PH:.3f}" '
        f'fill="#f8fafc" stroke="none"/>'
    )

    # ── Grid lines ────────────────────────────────────────────────────────────
    gsw = sw * 0.7
    for xt in x_ticks:
        gx = sx(xt)
        if _PX0 - 0.01 <= gx <= _PX1 + 0.01:
            out.append(
                f'<line x1="{gx:.3f}" y1="{_PY0:.3f}" x2="{gx:.3f}" y2="{_PY1:.3f}" '
                f'stroke="{_C_GRID}" stroke-width="{gsw:.3f}"/>'
            )
    for yt in y_ticks:
        gy = sy(yt)
        if _PY0 - 0.01 <= gy <= _PY1 + 0.01:
            out.append(
                f'<line x1="{_PX0:.3f}" y1="{gy:.3f}" x2="{_PX1:.3f}" y2="{gy:.3f}" '
                f'stroke="{_C_GRID}" stroke-width="{gsw:.3f}"/>'
            )

    # ── Axes ──────────────────────────────────────────────────────────────────
    ax_y = sy(0) if y_min <= 0 <= y_max else _PY1
    out.append(
        f'<line x1="{_PX0:.3f}" y1="{ax_y:.3f}" x2="{_PX1:.3f}" y2="{ax_y:.3f}" '
        f'stroke="{_C_AXIS}" stroke-width="{sw:.3f}"/>'
    )
    ax_x = sx(0) if x_min <= 0 <= x_max else _PX0
    out.append(
        f'<line x1="{ax_x:.3f}" y1="{_PY0:.3f}" x2="{ax_x:.3f}" y2="{_PY1:.3f}" '
        f'stroke="{_C_AXIS}" stroke-width="{sw:.3f}"/>'
    )

    # Plot border
    out.append(
        f'<rect x="{_PX0:.3f}" y="{_PY0:.3f}" width="{_PW:.3f}" height="{_PH:.3f}" '
        f'fill="none" stroke="{_C_AXIS}" stroke-width="{sw:.3f}"/>'
    )

    # ── Tick marks and labels ─────────────────────────────────────────────────
    for xt in x_ticks:
        gx = sx(xt)
        if _PX0 - 0.01 <= gx <= _PX1 + 0.01:
            out.append(
                f'<line x1="{gx:.3f}" y1="{_PY1:.3f}" '
                f'x2="{gx:.3f}" y2="{_PY1 + tick_len:.3f}" '
                f'stroke="{_C_AXIS}" stroke-width="{sw:.3f}"/>'
            )
            out.append(
                f'<text x="{gx:.3f}" y="{_PY1 + tick_len + fs_tick * 0.7:.3f}" '
                f'font-size="{fs_tick:.3f}" font-family="{_FONT}" '
                f'text-anchor="middle" dominant-baseline="middle" '
                f'fill="{_C_AXIS}">{_fmt(xt)}</text>'
            )
    for yt in y_ticks:
        gy = sy(yt)
        if _PY0 - 0.01 <= gy <= _PY1 + 0.01:
            out.append(
                f'<line x1="{_PX0:.3f}" y1="{gy:.3f}" '
                f'x2="{_PX0 - tick_len:.3f}" y2="{gy:.3f}" '
                f'stroke="{_C_AXIS}" stroke-width="{sw:.3f}"/>'
            )
            out.append(
                f'<text x="{_PX0 - tick_len - 0.4 * viz_scale:.3f}" y="{gy:.3f}" '
                f'font-size="{fs_tick:.3f}" font-family="{_FONT}" '
                f'text-anchor="end" dominant-baseline="middle" '
                f'fill="{_C_AXIS}">{_fmt(yt)}</text>'
            )

    # ── Trend line (dashed grey, always regression) ───────────────────────────
    if d.show_trend and slope is not None:
        def _clip_line(x0, x1, m, b, ylo, yhi):
            pts = []
            for xv in (x0, x1):
                yv = m * xv + b
                yv = max(ylo, min(yhi, yv))
                pts.append((sx(xv), sy(yv)))
            return pts

        tpts = _clip_line(x_min, x_max, slope, intercept, y_min, y_max)
        dash = 1.5 * viz_scale
        out.append(
            f'<line x1="{tpts[0][0]:.3f}" y1="{tpts[0][1]:.3f}" '
            f'x2="{tpts[1][0]:.3f}" y2="{tpts[1][1]:.3f}" '
            f'stroke="{_C_TREND}" stroke-width="{sw * 1.3:.3f}" '
            f'stroke-dasharray="{dash:.3f},{dash:.3f}"/>'
        )

    # ── Line of best fit (solid red) ──────────────────────────────────────────
    if d.show_line and _line_y is not None:
        line_pts = []
        for i in range(81):
            xv = x_min + i * (x_max - x_min) / 80
            yv = _line_y(xv)
            if yv is None:
                continue
            svgx = sx(xv)
            svgy = max(_PY0, min(_PY1, sy(yv)))
            line_pts.append((svgx, svgy))
        if len(line_pts) >= 2:
            pts_str = ' '.join(f'{p[0]:.3f},{p[1]:.3f}' for p in line_pts)
            out.append(
                f'<polyline points="{pts_str}" fill="none" '
                f'stroke="{_C_LINE}" stroke-width="{sw * 1.6:.3f}" '
                f'stroke-linejoin="round" stroke-linecap="round"/>'
            )

    # ── Intercept annotation (green) ──────────────────────────────────────────
    if d.intercept_annotation and _line_y is not None:
        yv = _line_y(0.0)
        if yv is not None and y_min <= yv <= y_max and x_min <= 0 <= x_max:
            ix, iy = sx(0.0), sy(yv)
            out.append(
                f'<circle cx="{ix:.3f}" cy="{iy:.3f}" r="{hl_r:.3f}" '
                f'fill="{_C_INTCPT}" stroke="white" stroke-width="{sw * 0.8:.3f}"/>'
            )
            out.append(
                f'<text x="{ix + 1.5 * viz_scale:.3f}" y="{iy - 1.2 * viz_scale:.3f}" '
                f'font-size="{fs_pt:.3f}" font-family="{_FONT}" '
                f'fill="{_C_INTCPT}">c = {_fmt(yv)}</text>'
            )

    # ── Gradient annotation (purple right-angle triangle) ────────────────────
    if d.gradient_annotation and slope is not None and _line_y is not None:
        mid_x = (x_min + x_max) / 2
        run   = (x_max - x_min) * 0.25
        x1v, x2v = mid_x - run / 2, mid_x + run / 2
        y1v = _line_y(x1v)
        y2v = _line_y(x2v)
        if y1v is not None and y2v is not None:
            gx1, gy1 = sx(x1v), sy(y1v)
            gx2, gy2 = sx(x2v), sy(y2v)
            dash = 0.8 * viz_scale
            out.append(
                f'<polyline points="{gx1:.3f},{gy1:.3f} {gx2:.3f},{gy1:.3f} '
                f'{gx2:.3f},{gy2:.3f}" fill="none" '
                f'stroke="{_C_GRAD}" stroke-width="{sw:.3f}" '
                f'stroke-dasharray="{dash:.3f},{dash:.3f}"/>'
            )
            out.append(
                f'<text x="{(gx1+gx2)/2:.3f}" y="{gy1 + 1.6 * viz_scale:.3f}" '
                f'font-size="{fs_pt:.3f}" font-family="{_FONT}" '
                f'text-anchor="middle" fill="{_C_GRAD}">run</text>'
            )
            my = (gy1 + gy2) / 2
            out.append(
                f'<text x="{gx2 + 1.5 * viz_scale:.3f}" y="{my:.3f}" '
                f'font-size="{fs_pt:.3f}" font-family="{_FONT}" '
                f'dominant-baseline="middle" fill="{_C_GRAD}">rise</text>'
            )
            out.append(
                f'<text x="{(gx1+gx2)/2:.3f}" y="{(gy1+gy2)/2 - 1.5 * viz_scale:.3f}" '
                f'font-size="{fs_pt:.3f}" font-family="{_FONT}" '
                f'text-anchor="middle" fill="{_C_GRAD}">m = {_fmt(round(slope, 4))}</text>'
            )

    # ── Prediction annotation (orange dashed) ─────────────────────────────────
    if d.predict_x is not None and _line_y is not None:
        pxv = d.predict_x
        pyv = _line_y(pxv)
        if pyv is not None:
            pxs, pys = sx(pxv), sy(pyv)
            dash = 1.0 * viz_scale
            # Vertical drop from line to x-axis
            out.append(
                f'<line x1="{pxs:.3f}" y1="{_PY1:.3f}" '
                f'x2="{pxs:.3f}" y2="{max(_PY0, min(_PY1, pys)):.3f}" '
                f'stroke="{_C_PREDICT}" stroke-width="{sw:.3f}" '
                f'stroke-dasharray="{dash:.3f},{dash:.3f}"/>'
            )
            # Horizontal from y-axis to point
            out.append(
                f'<line x1="{_PX0:.3f}" y1="{max(_PY0, min(_PY1, pys)):.3f}" '
                f'x2="{max(_PX0, min(_PX1, pxs)):.3f}" y2="{max(_PY0, min(_PY1, pys)):.3f}" '
                f'stroke="{_C_PREDICT}" stroke-width="{sw:.3f}" '
                f'stroke-dasharray="{dash:.3f},{dash:.3f}"/>'
            )
            out.append(
                f'<circle cx="{max(_PX0, min(_PX1, pxs)):.3f}" '
                f'cy="{max(_PY0, min(_PY1, pys)):.3f}" r="{hl_r:.3f}" '
                f'fill="{_C_PREDICT}" stroke="white" stroke-width="{sw * 0.8:.3f}"/>'
            )
            out.append(
                f'<text x="{max(_PX0, min(_PX1, pxs)) + 1.2 * viz_scale:.3f}" '
                f'y="{max(_PY0, min(_PY1, pys)) - 1.5 * viz_scale:.3f}" '
                f'font-size="{fs_pt:.3f}" font-family="{_FONT}" '
                f'fill="{_C_PREDICT}">({_fmt(pxv)}, {_fmt(round(pyv, 4))})</text>'
            )

    # ── Data points ───────────────────────────────────────────────────────────
    hl_set = set(d.highlight)
    for pxv, pyv in d.points:
        cxs, cys = sx(pxv), sy(pyv)
        if not (_PX0 - hl_r <= cxs <= _PX1 + hl_r and _PY0 - hl_r <= cys <= _PY1 + hl_r):
            continue
        is_hl = (pxv, pyv) in hl_set
        col   = _C_HL if is_hl else _C_POINT
        r     = hl_r  if is_hl else dot_r
        out.append(
            f'<circle cx="{cxs:.3f}" cy="{cys:.3f}" r="{r:.3f}" '
            f'fill="{col}" stroke="white" stroke-width="{sw * 0.6:.3f}"/>'
        )
        if is_hl:
            out.append(
                f'<text x="{cxs + 1.5 * viz_scale:.3f}" y="{cys - 1.3 * viz_scale:.3f}" '
                f'font-size="{fs_pt:.3f}" font-family="{_FONT}" '
                f'fill="{col}">({_fmt(pxv)}, {_fmt(pyv)})</text>'
            )

    # ── Axis labels ───────────────────────────────────────────────────────────
    mid_x_svg = (_PX0 + _PX1) / 2
    mid_y_svg = (_PY0 + _PY1) / 2

    out.append(
        f'<text x="{mid_x_svg:.3f}" y="{_VB_H - 1.2 * viz_scale:.3f}" '
        f'font-size="{fs_label:.3f}" font-family="{_FONT}" '
        f'text-anchor="middle" dominant-baseline="middle" '
        f'fill="{_C_AXIS}">{d.x_label}</text>'
    )
    y_lbl_x = 1.5 * viz_scale
    out.append(
        f'<text x="{y_lbl_x:.3f}" y="{mid_y_svg:.3f}" '
        f'font-size="{fs_label:.3f}" font-family="{_FONT}" '
        f'text-anchor="middle" dominant-baseline="middle" '
        f'fill="{_C_AXIS}" '
        f'transform="rotate(-90 {y_lbl_x:.3f} {mid_y_svg:.3f})">{d.y_label}</text>'
    )

    # ── Title ─────────────────────────────────────────────────────────────────
    if d.title:
        out.append(
            f'<text x="{mid_x_svg:.3f}" y="{_PY0 / 2:.3f}" '
            f'font-size="{fs_title:.3f}" font-family="{_FONT}" '
            f'text-anchor="middle" dominant-baseline="middle" '
            f'font-weight="bold" fill="{_C_AXIS}">{d.title}</text>'
        )

    return '\n'.join(out)
