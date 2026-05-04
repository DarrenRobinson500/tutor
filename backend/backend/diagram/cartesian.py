import re
import math
from dataclasses import dataclass, field
from typing import List, Optional

DIAGRAM_TYPE = "Cartesian"


@dataclass
class CartesianDiagram:
    xmin: float
    xmax: float
    ymin: float
    ymax: float
    eq: str = ""
    eq2: str = ""
    pos: List[float] = field(default_factory=lambda: [0.0, 0.0])
    w: float = 44.0
    h: float = 26.0
    square: bool = False
    x_label: str = ""
    y_label: str = ""
    x_tick_labels: List[str] = field(default_factory=list)
    vline: Optional[float] = None
    points: List[tuple] = field(default_factory=list)  # list of (x, y, label) tuples


def _get_str_val(key: str, line: str) -> str:
    """
    Extract a string value for `key` from the diagram spec line.
    Accepts all of:
      key: "value"      — double-quoted
      key: ''value''    — YAML-doubled single-quoted (PyYAML round-trip of 'value')
      key: 'value'      — single-quoted
      key: value        — unquoted, terminated by , ) or end of string
    """
    # Double-quoted: key: "value"
    m = re.search(rf"\b{key}:\s*\"([^\"]*)\"", line)
    if m:
        return m.group(1)
    # YAML-doubled single-quoted: key: ''value''  (must try before single-quoted)
    m = re.search(rf"\b{key}:\s*''([^']*)''", line)
    if m:
        return m.group(1)
    # Single-quoted: key: 'value'
    m = re.search(rf"\b{key}:\s*'([^']*)'", line)
    if m:
        return m.group(1)
    # Unquoted — everything up to the next , ) quote or end of string
    m = re.search(rf"\b{key}:\s*([^,)'\"]+)", line)
    if m:
        return m.group(1).strip()
    return ""


def parse(line: str) -> Optional[CartesianDiagram]:
    def get_num(key):
        m = re.search(rf'\b{key}:\s*(-?[\d.]+)', line)
        return float(m.group(1)) if m else None

    def get_str(key):
        return _get_str_val(key, line)

    # eq / eq2: accept double-quoted, YAML-doubled, single-quoted, or unquoted
    eq_match = (
        re.search(r'\beq:\s*"([^"]+)"', line)
        or re.search(r"\beq:\s*''([^']+)''", line)
        or re.search(r"\beq:\s*'([^']+)'", line)
        or re.search(r"\beq:\s*([^,)'\"]+)", line)
    )
    eq2_match = (
        re.search(r'\beq2:\s*"([^"]+)"', line)
        or re.search(r"\beq2:\s*''([^']+)''", line)
        or re.search(r"\beq2:\s*'([^']+)'", line)
        or re.search(r"\beq2:\s*([^,)'\"]+)", line)
    )
    pos_match    = re.search(r'\bpos:\s*\(\s*(-?[\d.]+)\s*,\s*(-?[\d.]+)\s*\)', line)
    square_match = re.search(r'\bsquare:\s*(true|false)', line)
    w_val = get_num("w")
    h_val = get_num("h")

    xmin = get_num("xmin")
    xmax = get_num("xmax")
    ymin = get_num("ymin")
    ymax = get_num("ymax")
    eq  = eq_match.group(1)  if eq_match  else ""
    eq2 = eq2_match.group(1) if eq2_match else ""

    if None in (xmin, xmax, ymin, ymax):
        return None

    pos    = [float(pos_match.group(1)), float(pos_match.group(2))] if pos_match else [0.0, 0.0]
    square = (square_match.group(1) == "true") if square_match else False

    xtl_raw = get_str("x_tick_labels")
    x_tick_labels = [s.strip() for s in xtl_raw.split(",")] if xtl_raw else []

    vline_m = re.search(r'\bvline:\s*"?(-?[\d.]+)"?', line)
    vline_val = float(vline_m.group(1)) if vline_m else None

    # points: ((x, y, "label"), ...) — labelled points, label is optional
    points_val = []
    points_m = re.search(r'\bpoints:\s*', line)
    if points_m:
        after = line[points_m.end():]
        # Match (x, y, "label") with optional label
        for m in re.finditer(r'\(\s*(-?[\d.]+)\s*,\s*(-?[\d.]+)\s*(?:,\s*"([^"]*)"\s*)?\)', after):
            points_val.append((float(m.group(1)), float(m.group(2)), m.group(3) or ""))

    return CartesianDiagram(
        xmin=xmin, xmax=xmax, ymin=ymin, ymax=ymax, eq=eq, eq2=eq2,
        pos=pos, w=w_val or 44.0, h=h_val or 26.0, square=square,
        x_label=get_str("x_label"), y_label=get_str("y_label"),
        x_tick_labels=x_tick_labels,
        vline=vline_val,
        points=points_val,
    )


def viewbox(d: CartesianDiagram) -> tuple:
    cx, cy = d.pos
    y_range = d.ymax - d.ymin
    x_range = d.xmax - d.xmin
    eff_w = d.h * x_range / y_range if y_range > 0 else d.w
    L = cx - eff_w / 2
    R = cx + eff_w / 2
    T = cy - d.h / 2
    B = cy + d.h / 2

    # Fixed margins (SVG units) for axis/tick labels that live outside the plot rect
    pad_left   = 9.0 if d.y_label else 7.0   # extra room when y_label shifted left of axis
    pad_right  = 4.0                          # "x" axis label + arrowhead
    pad_top    = 4.0 if d.y_label else 2.5   # extra room for y_label above arrowhead
    pad_bottom = 6.0 if d.x_label else 3.5   # extra room for x_label below tick numbers

    vb_min_x = L - pad_left
    vb_min_y = T - pad_top
    vb_w     = (R + pad_right) - vb_min_x
    vb_h     = ((B + pad_bottom) - vb_min_y) * 1.15
    vb_min_y -= (vb_h - ((B + pad_bottom) - (T - pad_top))) / 2
    return (vb_min_x, vb_min_y, vb_w, vb_h)


def _nice_step(approx: float) -> float:
    if approx <= 0:
        return 1.0
    mag = 10 ** math.floor(math.log10(approx))
    norm = approx / mag
    if norm < 1.5:
        return mag
    if norm < 3.5:
        return 2 * mag
    if norm < 7.5:
        return 5 * mag
    return 10 * mag


def _fmt_tick(n: float) -> str:
    if abs(n) < 1e-9:
        return "0"
    rounded = float(f"{n:.4g}")
    return str(int(rounded)) if rounded == int(rounded) else str(rounded)


def render(d: CartesianDiagram) -> str:
    # square: true expands the x range to fill the full d.w × d.h area (legacy behaviour).
    # Default: enforce equal scale by computing plot width from the data ranges so that
    # 1 unit on the x-axis has the same physical length as 1 unit on the y-axis.
    if d.square:
        x_center = (d.xmin + d.xmax) / 2
        x_half   = d.w * (d.ymax - d.ymin) / (2 * d.h)
        xmin = x_center - x_half
        xmax = x_center + x_half
    else:
        xmin = d.xmin
        xmax = d.xmax

    y_range = d.ymax - d.ymin
    x_range = xmax - xmin
    # Equal-scale plot width: keeps d.h fixed, adjusts w so scale_x == scale_y
    eff_w = d.h * x_range / y_range if y_range > 0 else d.w

    cx, cy = d.pos
    L = cx - eff_w / 2
    R = cx + eff_w / 2
    T = cy - d.h / 2
    B = cy + d.h / 2

    def to_svg_x(x):
        return L + ((x - xmin) / x_range) * eff_w

    def to_svg_y(y):
        return B - ((y - d.ymin) / y_range) * d.h

    axis_y = max(T, min(B, to_svg_y(0)))
    axis_x = max(L, min(R, to_svg_x(0)))

    sw = 0.2
    tick_len = 0.8
    font_size = 1.8
    x_step = _nice_step((xmax - xmin) / 8)
    y_step = _nice_step((d.ymax - d.ymin) / 6)

    x_grid_start = math.ceil(xmin / x_step) * x_step
    y_grid_start = math.ceil(d.ymin / y_step) * y_step

    clip_id = f"cc{str(cx).replace('.', '_').replace('-', 'n')}{str(cy).replace('.', '_').replace('-', 'n')}"

    out = []

    # Clip path
    out.append(
        f'<defs><clipPath id="{clip_id}">'
        f'<rect x="{L}" y="{T}" width="{eff_w}" height="{d.h}"/>'
        f'</clipPath></defs>'
    )

    # Background
    out.append(
        f'<rect x="{L}" y="{T}" width="{eff_w}" height="{d.h}" fill="white" stroke="#aaa" stroke-width="{sw}"/>'
    )

    # Custom x tick positions (when x_tick_labels provided)
    if d.x_tick_labels:
        n = len(d.x_tick_labels)
        x_tick_positions = (
            [xmin + i * (xmax - xmin) / (n - 1) for i in range(n)] if n > 1 else [xmin]
        )
    else:
        x_tick_positions = None

    # Grid lines — x
    if x_tick_positions is not None:
        for xp in x_tick_positions:
            sx = to_svg_x(xp)
            out.append(f'<line x1="{sx:.3f}" y1="{T}" x2="{sx:.3f}" y2="{B}" stroke="#e0e0e0" stroke-width="{sw}"/>')
    else:
        x = x_grid_start
        while x <= xmax + x_step * 0.01:
            sx = to_svg_x(x)
            out.append(f'<line x1="{sx:.3f}" y1="{T}" x2="{sx:.3f}" y2="{B}" stroke="#e0e0e0" stroke-width="{sw}"/>')
            x += x_step

    y = y_grid_start
    while y <= d.ymax + y_step * 0.01:
        sy = to_svg_y(y)
        out.append(f'<line x1="{L}" y1="{sy:.3f}" x2="{R}" y2="{sy:.3f}" stroke="#e0e0e0" stroke-width="{sw}"/>')
        y += y_step

    # Axes
    ax_sw = sw * 1.5
    out.append(f'<line x1="{L}" y1="{axis_y:.3f}" x2="{R}" y2="{axis_y:.3f}" stroke="black" stroke-width="{ax_sw}"/>')
    out.append(f'<line x1="{axis_x:.3f}" y1="{T}" x2="{axis_x:.3f}" y2="{B}" stroke="black" stroke-width="{ax_sw}"/>')

    # Arrowheads
    aw, ah = 0.7, 1.2
    out.append(f'<polygon points="{R},{axis_y:.3f} {R-ah},{axis_y-aw/2:.3f} {R-ah},{axis_y+aw/2:.3f}" fill="black"/>')
    out.append(f'<polygon points="{axis_x:.3f},{T} {axis_x-aw/2:.3f},{T+ah} {axis_x+aw/2:.3f},{T+ah}" fill="black"/>')

    # Axis labels (suppressed when a descriptive or tick label is provided)
    if not d.x_label and not d.x_tick_labels:
        out.append(f'<text x="{R+0.3}" y="{axis_y + font_size*0.4:.3f}" font-size="{font_size}" font-family="system-ui, -apple-system, sans-serif" font-style="italic" fill="black">x</text>')
    if not d.y_label:
        out.append(f'<text x="{axis_x - font_size*0.3:.3f}" y="{T-0.5}" text-anchor="middle" font-size="{font_size}" font-family="system-ui, -apple-system, sans-serif" font-style="italic" fill="black">y</text>')

    # Tick marks & labels
    label_offset = tick_len + font_size * 0.85

    # Optional descriptive labels
    if d.y_label:
        out.append(
            f'<text x="{axis_x - 4.6:.3f}" y="{T - 1.8:.3f}" '
            f'text-anchor="start" font-size="{font_size}" font-family="system-ui, -apple-system, sans-serif" fill="#333">'
            f'{d.y_label}</text>'
        )
    if d.x_label:
        tx_c = (L + R) / 2
        ty_xl = B + label_offset + font_size * 1.3
        out.append(
            f'<text x="{tx_c:.3f}" y="{ty_xl:.3f}" '
            f'text-anchor="middle" font-size="{font_size}" font-family="system-ui, -apple-system, sans-serif" fill="#333">'
            f'{d.x_label}</text>'
        )

    # X tick marks & labels
    if x_tick_positions is not None:
        for xp, lbl in zip(x_tick_positions, d.x_tick_labels):
            sx = to_svg_x(xp)
            out.append(f'<line x1="{sx:.3f}" y1="{axis_y - tick_len/2:.3f}" x2="{sx:.3f}" y2="{axis_y + tick_len/2:.3f}" stroke="black" stroke-width="{sw}"/>')
            out.append(f'<text x="{sx:.3f}" y="{axis_y + label_offset:.3f}" text-anchor="middle" font-size="{font_size}" font-family="system-ui, -apple-system, sans-serif" fill="#333">{lbl}</text>')
    else:
        x = x_grid_start
        while x <= xmax + x_step * 0.01:
            if abs(x) >= x_step * 0.01:
                sx = to_svg_x(x)
                out.append(f'<line x1="{sx:.3f}" y1="{axis_y - tick_len/2:.3f}" x2="{sx:.3f}" y2="{axis_y + tick_len/2:.3f}" stroke="black" stroke-width="{sw}"/>')
                out.append(f'<text x="{sx:.3f}" y="{axis_y + label_offset:.3f}" text-anchor="middle" font-size="{font_size}" font-family="system-ui, -apple-system, sans-serif" fill="#333">{_fmt_tick(x)}</text>')
            x += x_step

    y = y_grid_start
    while y <= d.ymax + y_step * 0.01:
        if abs(y) >= y_step * 0.01:
            sy = to_svg_y(y)
            out.append(f'<line x1="{axis_x - tick_len/2:.3f}" y1="{sy:.3f}" x2="{axis_x + tick_len/2:.3f}" y2="{sy:.3f}" stroke="black" stroke-width="{sw}"/>')
            out.append(f'<text x="{axis_x - tick_len - 0.3:.3f}" y="{sy + font_size*0.35:.3f}" text-anchor="end" font-size="{font_size}" font-family="system-ui, -apple-system, sans-serif" fill="#333">{_fmt_tick(y)}</text>')
        y += y_step


    def _normalise_eq(s: str) -> str:
        s = s.replace("^", "**")
        # Implicit multiplication: 3x → 3*x, 2(x+1) → 2*(x+1), )(x → )*(x
        s = re.sub(r'(\d)([a-zA-Z(])', r'\1*\2', s)
        s = re.sub(r'([a-zA-Z])\(', r'\1*(', s)  # x( → x*(  but not sin( — handled below
        # Restore math function calls broken by the rule above (sin, cos, tan, sqrt, …)
        s = re.sub(r'\b(sin|cos|tan|asin|acos|atan|atan2|sinh|cosh|tanh|sqrt|log|log2|log10|exp|abs|ceil|floor)\*\(', r'\1(', s)
        return s

    # Plot equation (skipped when eq is empty)
    if d.eq.strip():
        try:
            eq_norm = _normalise_eq(d.eq)
            safe_ns = {k: getattr(math, k) for k in dir(math) if not k.startswith("_")}
            safe_ns["abs"] = abs

            STEPS = 400
            segments = []
            current = []

            for i in range(STEPS + 1):
                x = xmin + (xmax - xmin) * (i / STEPS)
                try:
                    safe_ns["x"] = x
                    y_val = eval(eq_norm, {"__builtins__": {}}, safe_ns)  # noqa: S307
                    y_val = float(y_val)
                except Exception:
                    if len(current) > 1:
                        segments.append(current)
                    current = []
                    continue

                if not math.isfinite(y_val):
                    if len(current) > 1:
                        segments.append(current)
                    current = []
                    continue

                sx = to_svg_x(x)
                sy = max(T - 2, min(B + 2, to_svg_y(y_val)))
                cmd = f"M{sx:.3f},{sy:.3f}" if not current else f"L{sx:.3f},{sy:.3f}"
                current.append(cmd)

            if len(current) > 1:
                segments.append(current)

            for seg in segments:
                out.append(
                    f'<path d="{" ".join(seg)}" fill="none" stroke="#2563eb" '
                    f'stroke-width="{sw * 2.5}" stroke-linejoin="round" clip-path="url(#{clip_id})"/>'
                )
        except Exception:
            pass  # Invalid equation — omit curve silently

    # Plot second equation (eq2) in red
    if d.eq2.strip():
        try:
            eq2_norm = _normalise_eq(d.eq2)
            safe_ns2 = {k: getattr(math, k) for k in dir(math) if not k.startswith("_")}
            safe_ns2["abs"] = abs

            segments2 = []
            current2 = []

            for i in range(STEPS + 1):
                x = xmin + (xmax - xmin) * (i / STEPS)
                try:
                    safe_ns2["x"] = x
                    y_val = eval(eq2_norm, {"__builtins__": {}}, safe_ns2)  # noqa: S307
                    y_val = float(y_val)
                except Exception:
                    if len(current2) > 1:
                        segments2.append(current2)
                    current2 = []
                    continue

                if not math.isfinite(y_val):
                    if len(current2) > 1:
                        segments2.append(current2)
                    current2 = []
                    continue

                sx = to_svg_x(x)
                sy = max(T - 2, min(B + 2, to_svg_y(y_val)))
                cmd = f"M{sx:.3f},{sy:.3f}" if not current2 else f"L{sx:.3f},{sy:.3f}"
                current2.append(cmd)

            if len(current2) > 1:
                segments2.append(current2)

            for seg in segments2:
                out.append(
                    f'<path d="{" ".join(seg)}" fill="none" stroke="#dc2626" '
                    f'stroke-width="{sw * 2.5}" stroke-linejoin="round" clip-path="url(#{clip_id})"/>'
                )
        except Exception:
            pass

    # Vertical line at x = vline (only drawn when within the x range)
    if d.vline is not None and xmin <= d.vline <= xmax:
        sx = to_svg_x(d.vline)
        out.append(
            f'<path d="M{sx:.3f},{T} L{sx:.3f},{B}" fill="none" stroke="#2563eb" '
            f'stroke-width="{sw * 2.5}" clip-path="url(#{clip_id})"/>'
        )

    # Named points: blue filled dot + label
    dot_r = 0.9
    label_fs = font_size * 0.95
    for (px, py, label) in d.points:
        sx = to_svg_x(px)
        sy = to_svg_y(py)
        out.append(
            f'<circle cx="{sx:.3f}" cy="{sy:.3f}" r="{dot_r}" '
            f'fill="#16a34a" stroke="white" stroke-width="0.3" clip-path="url(#{clip_id})"/>'
        )
        if label:
            # Offset label so it doesn't overlap the dot — nudge up-right
            lx = sx + dot_r + 0.5
            ly = sy - dot_r - 0.3
            out.append(
                f'<text x="{lx:.3f}" y="{ly:.3f}" font-size="{label_fs}" '
                f'font-family="system-ui, -apple-system, sans-serif" '
                f'fill="#16a34a" font-weight="bold">{label}</text>'
            )

    return "\n".join(out)
