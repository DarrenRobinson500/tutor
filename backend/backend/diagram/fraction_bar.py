import re
from dataclasses import dataclass
from typing import Optional, Tuple

DIAGRAM_TYPE = "FractionBar"
SUPPORTS_VIZ_SCALE = True

# Syntax:
#   FractionBar(a: 2/3, b: 4/6, label: true)
#   FractionBar(a: 2/3, den: 12, label: true)   ← calculates equivalent fraction automatically
#   FractionBar(a: 2/3, den: 12, label_den: true) ← writes denominator to right of each bar
#
# Draws two equal-width horizontal fraction bars stacked vertically:
#   - Top bar subdivided by denominator of `a`, numerator sections highlighted
#   - Bottom bar subdivided by denominator of `b` (or derived from `den`), numerator sections highlighted
# label: true (default) shows the fraction above the top bar and below the bottom bar
# label_den: false (default) — when true, writes the denominator to the right of each bar


@dataclass
class FractionBarDiagram:
    a_num: int
    a_den: int
    b_num: Optional[int]
    b_den: Optional[int]
    label: bool = True
    label_den: bool = False
    pos: Tuple[float, float] = (0.0, 0.0)


def _parse_fraction(s: str) -> Optional[Tuple[int, int]]:
    s = s.strip()
    # LaTeX \frac{n}{d}
    m = re.fullmatch(r'\\frac\{(\d+)\}\{(\d+)\}', s)
    if m:
        return int(m.group(1)), int(m.group(2))
    # Plain n/d
    m = re.fullmatch(r'(\d+)/(\d+)', s)
    if m:
        return int(m.group(1)), int(m.group(2))
    # Whole number
    m = re.fullmatch(r'(\d+)', s)
    if m:
        return int(m.group(1)), 1
    return None


def parse(line: str) -> Optional[FractionBarDiagram]:
    a_match = re.search(r'\ba:\s*(\\frac\{\d+\}\{\d+\}|[\d/]+)', line)
    b_match = re.search(r'\bb:\s*(\\frac\{\d+\}\{\d+\}|[\d/]+)', line)
    den_match = re.search(r'\bden:\s*(\d+)', line)
    label_match = re.search(r'\blabel:\s*(true|false)', line, re.IGNORECASE)
    label_den_match = re.search(r'\blabel_den:\s*(true|false)', line, re.IGNORECASE)

    if not a_match:
        return None

    a = _parse_fraction(a_match.group(1))
    if not a:
        return None

    b = None
    if den_match:
        target_den = int(den_match.group(1))
        factor = target_den // a[1]
        b = (a[0] * factor, target_den)
    elif b_match:
        b = _parse_fraction(b_match.group(1))

    label = (label_match.group(1).lower() != 'false') if label_match else True
    label_den = (label_den_match.group(1).lower() == 'true') if label_den_match else False

    pos_match = re.search(r'\bpos:\s*\(\s*(-?[\d.]+)\s*,\s*(-?[\d.]+)\s*\)', line)
    pos = (float(pos_match.group(1)), float(pos_match.group(2))) if pos_match else (0.0, 0.0)

    return FractionBarDiagram(
        a_num=a[0], a_den=a[1],
        b_num=b[0] if b else None,
        b_den=b[1] if b else None,
        label=label,
        label_den=label_den,
        pos=pos,
    )


def viewbox(d: FractionBarDiagram) -> tuple:
    bar_w     = 40.0
    bar_h     =  8.0
    gap       =  1.5
    font_size =  3.5
    label_gap =  1.5
    pad       =  2.0

    single = d.b_num is None
    cx, cy = d.pos

    x_min = cx - bar_w / 2
    x_max = cx + bar_w / 2
    if d.label_den:
        x_max += label_gap + font_size * 2

    if single:
        if d.label:
            top_y = cy - (bar_h + font_size) / 2
            y_min = top_y - label_gap - font_size
            y_max = top_y + bar_h
        else:
            y_min = cy - bar_h / 2
            y_max = cy + bar_h / 2
    else:
        if d.label:
            top_y = cy - (2 * bar_h + gap + font_size) / 2
            bot_y = top_y + bar_h + gap
            y_min = top_y - label_gap - font_size
            y_max = bot_y + bar_h + label_gap + 2 * font_size
        else:
            total = 2 * bar_h + gap
            y_min = cy - total / 2
            y_max = cy + total / 2

    return (x_min - pad, y_min - pad, (x_max - x_min) + 2 * pad, (y_max - y_min) + 2 * pad)


def render(d: FractionBarDiagram, viz_scale: float = None) -> str:
    if viz_scale is None:
        viz_scale = 1.0

    bar_w = 40.0 * viz_scale
    bar_h = 8.0 * viz_scale
    gap = 1.5 * viz_scale          # vertical gap between the two bars
    sw = 0.5 * viz_scale
    font_size = 3.5 * viz_scale
    label_gap = 1.5 * viz_scale    # space between label and bar edge

    highlight = "#4a90d9"
    bar_bg = "#e8e8e8"
    border = "#333"

    cx, cy = d.pos
    x0 = cx - bar_w / 2
    x1 = cx + bar_w / 2

    single = d.b_num is None  # single-bar mode

    if single:
        if d.label:
            top_y = cy - (bar_h + font_size) / 2
        else:
            top_y = cy - bar_h / 2
    else:
        if d.label:
            top_y = cy - (2 * bar_h + gap + font_size) / 2
        else:
            top_y = cy - (2 * bar_h + gap) / 2
    bot_y = top_y + bar_h + gap

    out = []

    def draw_bar(y, num, den, fraction_str, label_above, show_den_label=True):
        cell_w = bar_w / den

        # Background
        out.append(
            f'<rect x="{x0:.3f}" y="{y:.3f}" width="{bar_w:.3f}" height="{bar_h:.3f}" '
            f'fill="{bar_bg}" stroke="{border}" stroke-width="{sw}"/>'
        )

        # Highlighted cells (left-aligned)
        for i in range(num):
            cell_x = x0 + i * cell_w
            out.append(
                f'<rect x="{cell_x:.3f}" y="{y:.3f}" width="{cell_w:.3f}" height="{bar_h:.3f}" '
                f'fill="{highlight}" stroke="none"/>'
            )

        # Division lines (internal borders only)
        for i in range(1, den):
            lx = x0 + i * cell_w
            out.append(
                f'<line x1="{lx:.3f}" y1="{y:.3f}" x2="{lx:.3f}" y2="{y + bar_h:.3f}" '
                f'stroke="{border}" stroke-width="{sw}"/>'
            )

        # Outer border on top (drawn last so it sits above highlights)
        out.append(
            f'<rect x="{x0:.3f}" y="{y:.3f}" width="{bar_w:.3f}" height="{bar_h:.3f}" '
            f'fill="none" stroke="{border}" stroke-width="{sw}"/>'
        )

        # Fraction label (above top bar / below bottom bar)
        if d.label:
            if label_above:
                anchor_y_text = y - label_gap
            else:
                anchor_y_text = y + bar_h + label_gap + font_size

            out.append(
                f'<text x="{cx:.3f}" y="{anchor_y_text:.3f}" text-anchor="middle" '
                f'font-size="{font_size:.3f}" font-family="system-ui, -apple-system, sans-serif" '
                f'fill="#333">{fraction_str}</text>'
            )

        # Denominator label to the right of the bar
        if d.label_den and show_den_label:
            den_x = x1 + label_gap
            den_y = y + bar_h / 2 + font_size * 0.35  # vertically centred
            out.append(
                f'<text x="{den_x:.3f}" y="{den_y:.3f}" text-anchor="start" '
                f'font-size="{font_size:.3f}" font-family="system-ui, -apple-system, sans-serif" '
                f'fill="#333">{den}</text>'
            )

    draw_bar(top_y, d.a_num, d.a_den, f"{d.a_num}/{d.a_den}", label_above=True, show_den_label=single)
    if not single:
        draw_bar(bot_y, d.b_num, d.b_den, f"{d.b_num}/{d.b_den}", label_above=False, show_den_label=True)

    return "\n".join(out)
