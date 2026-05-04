import re
import math
from dataclasses import dataclass, field
from typing import Optional

DIAGRAM_TYPE = "AlgebraTable"

# Syntax:
#   AlgebraTable(x_min: 1, x_max: 7, expr: "x+2", blank: 4)
#   AlgebraTable(x_min: 1, x_max: 7, expr: "x+2", blanks: "3,4,5", highlight: 3)
#
# blank:     single x value to leave blank (legacy/simple mode)
# blanks:    comma-separated x values to leave blank (multi-step mode)
# highlight: which blank is currently highlighted yellow; others show as light grey


@dataclass
class AlgebraTableDiagram:
    x_min: int = 1
    x_max: int = 7
    expr: str = "x"
    blank: int = 0                         # legacy single-blank
    blanks: list = field(default_factory=list)  # multi-blank list
    highlight: int = 0                     # active (yellow) blank; 0 = auto
    step: int = 1                          # increment between x values
    label_1: str = ""                      # row 1 label (default: "x")
    label_2: str = ""                      # row 2 label (default: expr)


def parse(line: str) -> Optional[AlgebraTableDiagram]:
    def get_int(key, default):
        m = re.search(rf'\b{key}:\s*(-?\d+)', line)
        return int(m.group(1)) if m else default

    def get_str(key, default):
        m = re.search(rf'\b{key}:\s*"([^"]*)"', line)
        if m:
            return m.group(1)
        m = re.search(rf'\b{key}:\s*([^,)\s]+)', line)
        return m.group(1) if m else default

    x_min = get_int("x_min", 1)
    x_max = get_int("x_max", 7)
    blank = get_int("blank", 0)
    step  = get_int("step", 1)
    expr    = get_str("expr", "x")
    label_1 = get_str("label_1", "")
    label_2 = get_str("label_2", "")

    # Parse blanks: "3,4,5"
    blanks = []
    m = re.search(r'\bblanks:\s*"([^"]*)"', line)
    if m:
        blanks = [int(v.strip()) for v in m.group(1).split(',') if v.strip().lstrip('-').isdigit()]

    highlight = get_int("highlight", blanks[0] if blanks else 0)

    x_vals = list(range(x_min, x_max + 1, max(step, 1)))
    if len(x_vals) < 2 or len(x_vals) > 12:
        return None

    return AlgebraTableDiagram(
        x_min=x_min, x_max=x_max, expr=expr,
        blank=blank, blanks=blanks, highlight=highlight,
        step=step, label_1=label_1, label_2=label_2,
    )


def _svg_label(text: str, x: float, y: float, fs: float, anchor: str, extra_attrs: str = "") -> str:
    """Render a label string as an SVG <text> element, converting ^n / ^{n} into <tspan> superscripts."""
    # Split on ^{...} or ^X patterns
    parts = re.split(r'\^\{([^}]*)\}|\^(-?[a-zA-Z0-9]+)', text)
    # re.split with two capturing groups gives: [normal, group1, group2, normal, ...]
    # When ^{...} matches, group1 has content and group2 is None; vice-versa for ^X.
    if len(parts) == 1:
        # No superscripts — plain text element
        return (
            f'<text x="{x:.3f}" y="{y:.3f}" font-size="{fs:.3f}" '
            f'font-family="system-ui, -apple-system, sans-serif" '
            f'text-anchor="{anchor}" dominant-baseline="middle" {extra_attrs}>'
            f'{text}</text>'
        )

    sup_fs   = fs * 0.72
    sup_dy   = -fs * 0.48   # shift up
    reset_dy =  fs * 0.48   # shift back down

    spans = []
    i = 0
    while i < len(parts):
        chunk = parts[i]
        if chunk:
            if i == 0:
                spans.append(f'<tspan>{chunk}</tspan>')
            else:
                spans.append(f'<tspan dy="{reset_dy:.3f}">{chunk}</tspan>')
        # Next two slots are the two capture groups from the split
        g1 = parts[i + 1] if i + 1 < len(parts) else None
        g2 = parts[i + 2] if i + 2 < len(parts) else None
        sup = g1 if g1 is not None else (g2 if g2 is not None else None)
        if sup is not None:
            spans.append(
                f'<tspan dy="{sup_dy:.3f}" font-size="{sup_fs:.3f}">{sup}</tspan>'
            )
        i += 3

    return (
        f'<text x="{x:.3f}" y="{y:.3f}" font-size="{fs:.3f}" '
        f'font-family="system-ui, -apple-system, sans-serif" '
        f'text-anchor="{anchor}" dominant-baseline="middle" {extra_attrs}>'
        + "".join(spans)
        + '</text>'
    )


def _eval_expr(expr_str: str, x_val: int):
    """Evaluate expr_str at x=x_val using sympy. Returns numeric value or None.

    Returns an exact "p/q" fraction string for non-integer rational results so
    that answer comparison works correctly when a student types e.g. "5/3".
    """
    try:
        from sympy import Symbol, Rational
        from sympy.parsing.sympy_parser import (
            parse_expr, standard_transformations,
            implicit_multiplication_application,
        )
        x = Symbol("x")
        transformations = standard_transformations + (implicit_multiplication_application,)
        # Normalise ^ to ** so both "3^x" and "3**x" evaluate correctly
        normalised = expr_str.replace("^", "**")
        result = parse_expr(normalised, local_dict={"x": x}, transformations=transformations)
        val = result.subs(x, x_val)
        # Return exact fraction for non-integer rationals (e.g. 5/3, 1/4)
        if isinstance(val, Rational) and val.q != 1:
            return f"{val.p}/{val.q}"
        f = float(val)
        return int(f) if f == int(f) else round(f, 4)
    except Exception:
        return None


def _fmt(val) -> str:
    if val is None:
        return "?"
    return str(val)


def _compute_layout(d: AlgebraTableDiagram):
    """Returns (total_w, label_w, data_w, font_size).

    Expands the label column if the expression label is wider than the default,
    increasing total_w while keeping data column width constant.
    """
    x_vals = list(range(d.x_min, d.x_max + 1, max(d.step, 1)))
    n_data_cols = len(x_vals)

    BASE_W     = 56.0
    TARGET_FS  = 2.16
    data_w     = BASE_W / (1.5 + n_data_cols)
    label_w    = 1.5 * data_w
    font_size  = min(data_w * 0.32, TARGET_FS)

    # Estimate rendered width of the label text (bold, system-ui).
    # Strip ^{...} / ^n superscripts — they're raised and narrow.
    if d.label_2:
        label_text = d.label_2
    else:
        from ..render.format import ExprFormat
        label_text = ExprFormat().format(d.expr)
    base_text  = re.sub(r'\^(\{[^}]*\}|[a-zA-Z0-9]+)', '', label_text)
    char_w     = font_size * 0.65          # ~0.65 em per char for bold system-ui
    pad_l      = label_w * 0.08 + 0.5     # left indent + right breathing room
    needed_w   = len(base_text) * char_w + pad_l

    if needed_w > label_w:
        label_w = needed_w
    total_w = label_w + n_data_cols * data_w

    return total_w, label_w, data_w, font_size


def viewbox(d: AlgebraTableDiagram) -> tuple:
    total_w, _, _, _ = _compute_layout(d)
    cell_h = 6.5
    total_h = cell_h * 2
    pad_x, pad_y = 2.0, 2.0
    vb_w = total_w + 2 * pad_x
    vb_h = total_h + 2 * pad_y
    return (-vb_w / 2, -vb_h / 2, vb_w, vb_h)


def render(d: AlgebraTableDiagram) -> str:
    x_vals = list(range(d.x_min, d.x_max + 1, max(d.step, 1)))
    n_data_cols = len(x_vals)
    n_cols = n_data_cols + 1      # label column + data columns

    total_w, label_w, data_w, font_size = _compute_layout(d)
    cell_h  = 6.5
    total_h = cell_h * 2

    x0 = -total_w / 2
    y0 = -total_h / 2

    def col_x(col):
        return x0 if col == 0 else x0 + label_w + (col - 1) * data_w

    def col_w(col):
        return label_w if col == 0 else data_w

    FILL_HEADER      = "#e8e8e8"
    FILL_HIGHLIGHT   = "#fff9c4"   # active blank — yellow
    FILL_BLANK_OTHER = "#f0f0f0"   # other blanks — light grey
    FILL_NORMAL      = "#ffffff"
    STROKE           = "#888888"
    SW               = 0.15

    # Build sets for fast lookup
    all_blanks = set(d.blanks) | ({d.blank} if d.blank else set())
    active = d.highlight if d.highlight else (d.blanks[0] if d.blanks else d.blank)

    out = []

    # Draw filled cells (no stroke — horizontal lines added separately)
    for row in range(2):
        for col in range(n_cols):
            cx = col_x(col)
            cw = col_w(col)
            cy = y0 + row * cell_h

            is_label_col = (col == 0)
            x_val = x_vals[col - 1] if col > 0 else None
            is_blank = row == 1 and col > 0 and x_val in all_blanks
            is_active = is_blank and x_val == active

            if is_label_col:
                fill = FILL_HEADER
            elif is_active:
                fill = FILL_HIGHLIGHT
            elif is_blank:
                fill = FILL_BLANK_OTHER
            else:
                fill = FILL_NORMAL

            out.append(
                f'<rect x="{cx:.3f}" y="{cy:.3f}" '
                f'width="{cw:.3f}" height="{cell_h:.3f}" '
                f'fill="{fill}" stroke="none"/>'
            )

            # Cell text
            tx = cx + cw * 0.08 if is_label_col else cx + cw / 2  # left-pad label col
            ty = cy + cell_h / 2

            if row == 0:
                text = (d.label_1 if d.label_1 else "x") if is_label_col else str(x_val)
                fs = font_size
            else:
                if is_label_col:
                    if d.label_2:
                        text = d.label_2
                    else:
                        from ..render.format import ExprFormat
                        text = ExprFormat().format(d.expr)
                    fs = font_size
                elif is_blank:
                    text = ""
                    fs = font_size
                else:
                    text = _fmt(_eval_expr(d.expr, x_val))
                    fs = font_size

            if text:
                anchor     = "start"  if is_label_col else "middle"
                extra_attrs = 'font-weight="bold"' if is_label_col else ''
                out.append(_svg_label(text, tx, ty, fs, anchor, extra_attrs))

    # Horizontal lines only: top, middle, bottom
    for hy in [y0, y0 + cell_h, y0 + total_h]:
        out.append(
            f'<line x1="{x0:.3f}" y1="{hy:.3f}" x2="{x0 + total_w:.3f}" y2="{hy:.3f}" '
            f'stroke="{STROKE}" stroke-width="{SW}"/>'
        )

    return "\n".join(out)
