import re
import math
from dataclasses import dataclass
from typing import Optional, List, Tuple

DIAGRAM_TYPE = "BoxPlot"
SUPPORTS_VIZ_SCALE = True

_FONT_SIZE = 2.2   # base font size at viz_scale = 1.0

# Examples:
# BoxPlot(data: [3, 5, 7, 9, 11, 13, 15])
# BoxPlot(data: [3, 5, 7, 9, 11], label: "Class A", data2: [4, 6, 8, 10, 14], label2: "Class B")


@dataclass
class BoxPlotDiagram:
    type: str
    datasets: List[Tuple[str, List[float]]]  # [(label, [values]), ...]


def _extract_bracket(s: str, start: int) -> Tuple[str, int]:
    depth = 0
    for i in range(start, len(s)):
        if s[i] == '[':
            depth += 1
        elif s[i] == ']':
            depth -= 1
            if depth == 0:
                return s[start + 1:i], i + 1
    return s[start + 1:], len(s)


def _parse_kv(inner: str) -> dict:
    keys = {}
    i = 0
    while i < len(inner):
        while i < len(inner) and inner[i] in ' \t,':
            i += 1
        if i >= len(inner):
            break
        colon = inner.find(':', i)
        if colon == -1:
            break
        key = inner[i:colon].strip()
        i = colon + 1
        while i < len(inner) and inner[i] in ' \t':
            i += 1
        if i >= len(inner):
            break
        if inner[i] == '[':
            val, i = _extract_bracket(inner, i)
            keys[key] = '[' + val + ']'
        elif inner[i] in ('"', "'", '“', '”'):
            j = i + 1
            while j < len(inner) and inner[j] not in ('"', "'", '“', '”'):
                j += 1
            keys[key] = inner[i + 1:j]
            i = j + 1
        else:
            j = i
            while j < len(inner) and inner[j] != ',':
                j += 1
            keys[key] = inner[i:j].strip()
            i = j
    return keys


def parse(line: str) -> Optional[BoxPlotDiagram]:
    line = line.strip()
    if not line.startswith('BoxPlot(') or not line.endswith(')'):
        return None
    inner = line[len('BoxPlot('):-1].strip()

    kv = _parse_kv(inner)

    datasets = []
    for suffix in ('', '2'):
        key = 'data' + suffix
        if key not in kv:
            continue
        nums = [float(m.group()) for m in re.finditer(r'-?\d+(?:\.\d+)?', kv[key])]
        if not nums:
            continue
        label = kv.get('label' + suffix, '')
        datasets.append((label, nums))

    return BoxPlotDiagram(type=DIAGRAM_TYPE, datasets=datasets) if datasets else None


def _five_number_summary(data: List[float]) -> Tuple[float, float, float, float, float]:
    s = sorted(data)
    n = len(s)

    def _med(lst):
        k = len(lst)
        mid = k // 2
        return lst[mid] if k % 2 else (lst[mid - 1] + lst[mid]) / 2

    median = _med(s)
    mid = n // 2
    lower = s[:mid]
    upper = s[mid + 1:] if n % 2 else s[mid:]
    q1 = _med(lower) if lower else float(s[0])
    q3 = _med(upper) if upper else float(s[-1])
    return float(s[0]), float(q1), float(median), float(q3), float(s[-1])


def render(diagram: BoxPlotDiagram, viz_scale: float = 1.0) -> str:
    datasets = diagram.datasets
    summaries = [_five_number_summary(vals) for _, vals in datasets]

    all_vals = [v for _, data in datasets for v in data]
    data_min, data_max = min(all_vals), max(all_vals)
    span = data_max - data_min or 1.0
    pad = span * 0.12
    axis_min = data_min - pad
    axis_max = data_max + pad

    plot_x0 = -22.0
    plot_x1 = 22.0

    def to_x(v):
        return plot_x0 + (v - axis_min) / (axis_max - axis_min) * (plot_x1 - plot_x0)

    label_cx = (plot_x0 + plot_x1) / 2

    n = len(datasets)
    if n == 1:
        box_centers = [0.0]
        half_h = 2.1
        axis_y = 7.0
    else:
        box_centers = [-5.0, 5.5]
        half_h = 1.8
        axis_y = 12.0

    font_size = _FONT_SIZE * viz_scale
    # Five-number labels sit just above the box top; dataset label clears above those
    five_lbl_gap = 0.9           # baseline to box-top gap
    dataset_lbl_gap = font_size + 1.5  # clears above five-number labels

    colors = ['#4e79a7', '#e15759']
    frags = []

    for idx, (summary, (label, _)) in enumerate(zip(summaries, datasets)):
        mn, q1, med, q3, mx = summary
        cy = box_centers[idx]
        c = colors[idx % 2]
        cap = half_h * 0.5

        x_mn  = to_x(mn)
        x_q1  = to_x(q1)
        x_med = to_x(med)
        x_q3  = to_x(q3)
        x_mx  = to_x(mx)
        yt, yb = cy - half_h, cy + half_h

        # Whiskers
        frags.append(f'<line x1="{x_mn:.2f}" y1="{cy:.2f}" x2="{x_q1:.2f}" y2="{cy:.2f}" stroke="black" stroke-width="0.125"/>')
        frags.append(f'<line x1="{x_q3:.2f}" y1="{cy:.2f}" x2="{x_mx:.2f}" y2="{cy:.2f}" stroke="black" stroke-width="0.125"/>')
        # Whisker end caps
        frags.append(f'<line x1="{x_mn:.2f}" y1="{cy-cap:.2f}" x2="{x_mn:.2f}" y2="{cy+cap:.2f}" stroke="black" stroke-width="0.125"/>')
        frags.append(f'<line x1="{x_mx:.2f}" y1="{cy-cap:.2f}" x2="{x_mx:.2f}" y2="{cy+cap:.2f}" stroke="black" stroke-width="0.125"/>')
        # IQR box
        frags.append(
            f'<rect x="{x_q1:.2f}" y="{yt:.2f}" width="{x_q3-x_q1:.2f}" height="{yb-yt:.2f}" '
            f'fill="{c}" fill-opacity="0.25" stroke="{c}" stroke-width="0.25"/>'
        )
        # Median line
        frags.append(f'<line x1="{x_med:.2f}" y1="{yt:.2f}" x2="{x_med:.2f}" y2="{yb:.2f}" stroke="{c}" stroke-width="0.25"/>')

        # All text suppressed on pass 1 so it doesn't inflate the bbox
        if viz_scale != 1.0:
            # Five-number summary values above whiskers/box
            five_y = yt - five_lbl_gap
            for val, xv in ((mn, x_mn), (q1, x_q1), (med, x_med), (q3, x_q3), (mx, x_mx)):
                lbl = str(int(val)) if val == int(val) else f'{val:g}'
                frags.append(
                    f'<text x="{xv:.2f}" y="{five_y:.2f}" font-size="{font_size:.3f}" '
                    f'text-anchor="middle" dominant-baseline="auto" fill="black">{lbl}</text>'
                )

            # Dataset label centered above, clearing the five-number labels
            if label:
                frags.append(
                    f'<text x="{label_cx:.2f}" y="{yt - dataset_lbl_gap:.2f}" font-size="{font_size:.3f}" '
                    f'text-anchor="middle" dominant-baseline="auto" fill="{c}">{label}</text>'
                )

    # Axis line
    frags.append(
        f'<line x1="{plot_x0:.2f}" y1="{axis_y:.2f}" x2="{plot_x1:.2f}" y2="{axis_y:.2f}" '
        f'stroke="#999" stroke-width="0.2"/>'
    )

    # Axis ticks at consistent round-number intervals
    raw_span = axis_max - axis_min
    rough = raw_span / 8
    mag = 10 ** math.floor(math.log10(rough)) if rough > 0 else 1
    step = next((m * mag for m in (1, 2, 5, 10) if m * mag >= rough), 10 * mag)
    first_tick = math.ceil(axis_min / step) * step
    tick_vals = []
    v = first_tick
    while v <= axis_max + 1e-9:
        tick_vals.append(round(v, 10))
        v = round(v + step, 10)

    for v in tick_vals:
        xv = to_x(v)
        frags.append(f'<line x1="{xv:.2f}" y1="{axis_y:.2f}" x2="{xv:.2f}" y2="{axis_y+1.0:.2f}" stroke="#999" stroke-width="0.2"/>')
        if viz_scale != 1.0:
            lbl = str(int(v)) if v == int(v) else f'{v:g}'
            frags.append(f'<text x="{xv:.2f}" y="{axis_y+font_size+1.0:.2f}" font-size="{font_size:.3f}" text-anchor="middle" fill="#999">{lbl}</text>')

    return '\n'.join(frags)
