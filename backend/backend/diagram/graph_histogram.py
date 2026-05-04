
import re
import math
from dataclasses import dataclass
from typing import Optional, Tuple, List

DIAGRAM_TYPE = "GraphHistogram"

# Syntax:
#   GraphHistogram(points: [("1-5", 3), ("6-10", 7), ("11-15", 5)], pos: (0,0))
#   GraphHistogram(points: [("1-5", 3), ("6-10", 7)], pos: (0,0), freq: true)


@dataclass
class GraphHistogramDiagram:
    type: str
    points: List[Tuple[str, float]]   # [(label, value), ...]
    pos: Tuple[float, float]
    freq: bool = False
    label: bool = False


# Accept pairs like ("Label", 12.3); allow straight or curly quotes
PAIR_REGEX = re.compile(
    r'\(\s*[\u201c\u201d"](.*?)[\u201c\u201d"]\s*,\s*(-?\d+(?:\.\d*)?)\s*\)'
)


def parse(line: str) -> Optional[GraphHistogramDiagram]:
    if not line.startswith("GraphHistogram"):
        return None

    pts_match = re.search(r'points:\s*\[(.+?)\]', line)
    if not pts_match:
        return None

    points: List[Tuple[str, float]] = []
    for label, value in PAIR_REGEX.findall(pts_match.group(1)):
        points.append((label, float(value)))

    if not points:
        return None

    pos_match = re.search(r'pos:\s*\(\s*(-?[\d.]+)\s*,\s*(-?[\d.]+)\s*\)', line)
    pos = (float(pos_match.group(1)), float(pos_match.group(2))) if pos_match else (0.0, 0.0)

    freq_match = re.search(r'\bfreq:\s*(true|false)', line)
    freq = (freq_match.group(1) == "true") if freq_match else False

    label_match = re.search(r'\blabel:\s*(true|false)', line)
    label = (label_match.group(1) == "true") if label_match else False

    return GraphHistogramDiagram(type=DIAGRAM_TYPE, points=points, pos=pos, freq=freq, label=label)


def _nice_step(approx: float) -> float:
    """Round approx up to a 'nice' step: 1, 2, 5 or multiples of 10."""
    if approx <= 0:
        return 1.0
    mag = 10 ** math.floor(math.log10(approx))
    norm = approx / mag
    if norm <= 1.0:
        return mag
    if norm <= 2.0:
        return 2 * mag
    if norm <= 5.0:
        return 5 * mag
    return 10 * mag


def render(diagram: GraphHistogramDiagram) -> str:
    """
    Returns SVG fragments (no <svg> wrapper) for the engine to wrap.
    """
    cols = diagram.points
    px, py = diagram.pos

    # --- Layout constants ---
    max_chart_height = 18.0
    bar_width = 4.0
    y_axis_gap = 1.5   # gap between y-axis line and left edge of first bar

    n = len(cols)
    total_bars_width = n * bar_width

    # Centre the chart (y-axis + gap + bars) on px
    chart_total_width = y_axis_gap + total_bars_width
    y_axis_x = px - chart_total_width / 2.0
    x0 = y_axis_x + y_axis_gap           # left edge of first bar
    y_base = py + max_chart_height / 2.0  # baseline (SVG y grows downward)

    max_val = max(v for _, v in cols) if cols else 0.0
    scale = (max_chart_height / max_val) if max_val != 0 else 0.0

    # --- Y-axis tick spacing ---
    target_ticks = 5
    step = _nice_step(max_val / target_ticks)
    tick_vals = []
    v = step
    while v <= max_val + step * 0.01:
        tick_vals.append(v)
        v += step

    frags: List[str] = []

    # Baseline — extended half a bar-width beyond the last bar so the freq
    # polygon anchor sits on the axis rather than past it.
    x_axis_right = x0 + total_bars_width + bar_width / 2
    frags.append(
        f'<line x1="{y_axis_x:.2f}" y1="{y_base:.2f}" '
        f'x2="{x_axis_right:.2f}" y2="{y_base:.2f}" '
        f'stroke="black" stroke-width="0.3"/>'
    )

    # Y-axis
    top_y = y_base - max_val * scale
    frags.append(
        f'<line x1="{y_axis_x:.2f}" y1="{y_base:.2f}" '
        f'x2="{y_axis_x:.2f}" y2="{top_y:.2f}" '
        f'stroke="black" stroke-width="0.3"/>'
    )

    # Y-axis major ticks, sub-ticks, and labels
    sub_step = step / 2
    sub_v = sub_step
    while sub_v < max_val - sub_step * 0.01:
        # Skip positions that coincide with a major tick
        is_major = any(abs(sub_v - tv) < sub_step * 0.01 for tv in tick_vals)
        if not is_major:
            sy = y_base - sub_v * scale
            frags.append(
                f'<line x1="{y_axis_x - 0.3:.2f}" y1="{sy:.2f}" '
                f'x2="{y_axis_x:.2f}" y2="{sy:.2f}" '
                f'stroke="black" stroke-width="0.15"/>'
            )
        sub_v += sub_step

    for tv in tick_vals:
        ty = y_base - tv * scale
        label = str(int(tv)) if tv == int(tv) else f"{tv:g}"
        frags.append(
            f'<line x1="{y_axis_x - 0.5:.2f}" y1="{ty:.2f}" '
            f'x2="{y_axis_x:.2f}" y2="{ty:.2f}" '
            f'stroke="black" stroke-width="0.2"/>'
        )
        frags.append(
            f'<text x="{y_axis_x - 0.8:.2f}" y="{ty + 0.6:.2f}" '
            f'font-size="1.8" text-anchor="end" fill="#333">{label}</text>'
        )

    # Bars, category labels, value labels
    freq_points: List[Tuple[float, float]] = []

    for i, (label, value) in enumerate(cols):
        h = value * scale if scale else 0.0
        x = x0 + i * bar_width
        y = y_base - h

        # Bar — touching neighbours; thin white stroke creates a visible seam
        frags.append(
            f'<rect x="{x:.2f}" y="{y:.2f}" width="{bar_width:.2f}" height="{h:.2f}" '
            f'fill="#4e79a7" stroke="white" stroke-width="0.15"/>'
        )

        # Category label — angled so long labels don't overlap
        cx_lbl = x + bar_width / 2
        cy_lbl = y_base + 1.5
        frags.append(
            f'<text x="{cx_lbl:.2f}" y="{cy_lbl:.2f}" '
            f'font-size="2.0" text-anchor="end" fill="#333" '
            f'transform="rotate(-40, {cx_lbl:.2f}, {cy_lbl:.2f})">{label}</text>'
        )

        # Value label above bar (integer if whole) — only if label: true
        if diagram.label:
            value_str = str(int(value)) if value == int(value) else f"{value:g}"
            frags.append(
                f'<text x="{cx_lbl:.2f}" y="{y - 0.8:.2f}" '
                f'font-size="2" text-anchor="middle" fill="#333">{value_str}</text>'
            )

        if diagram.freq:
            freq_points.append((cx_lbl, y))

    # Frequency polygon
    if diagram.freq and freq_points:
        # Left anchor: clamp to the y-axis so the line never overhangs left.
        # Right anchor: sits on the extended x-axis (one half-bar past last bar).
        start_x = max(freq_points[0][0] - bar_width, y_axis_x)
        end_x   = x_axis_right
        pts = [(start_x, y_base)] + freq_points + [(end_x, y_base)]
        pts_str = " ".join(f"{fx:.2f},{fy:.2f}" for fx, fy in pts)
        frags.append(
            f'<polyline points="{pts_str}" '
            f'fill="none" stroke="#e15759" stroke-width="0.35" '
            f'stroke-linejoin="round" stroke-linecap="round"/>'
        )
        # Dot at each bar midpoint
        for fx, fy in freq_points:
            frags.append(
                f'<circle cx="{fx:.2f}" cy="{fy:.2f}" r="0.4" fill="#e15759"/>'
            )

    # Invisible spacer so the auto-zoom engine reserves room for angled labels
    frags.append(
        f'<line x1="{y_axis_x - 3:.2f}" y1="{y_base + 9:.2f}" '
        f'x2="{x0 + total_bars_width:.2f}" y2="{y_base + 9:.2f}" '
        f'stroke="black" stroke-width="0.001"/>'
    )

    return "\n".join(frags)
