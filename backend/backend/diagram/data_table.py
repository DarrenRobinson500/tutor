import re
from dataclasses import dataclass, field
from typing import List, Optional

DIAGRAM_TYPE = "DataTable"

# Syntax:
#   DataTable(headers: [Month, Rainfall], rows: [(Jan, 45), (Feb, 62), (Mar, 38)])
#   DataTable(headers: [x, y=2x+1], rows: [(1, 3), (2, 5), (3, 7)])
#   DataTable(headers: [, 2020, 2021, 2022], rows: [(Pop, 45, 52, 61)], label_col: true)
#
# label_col: true  — shades the first data column grey as well as the header row,
#                    making it act as a row-header column.


@dataclass
class DataTableDiagram:
    headers: List[str] = field(default_factory=list)
    rows: List[List[str]] = field(default_factory=list)
    label_col: bool = False   # also shade first column grey


def _split_csv(text: str) -> List[str]:
    """Split comma-separated values, respecting quoted strings."""
    items: List[str] = []
    current: List[str] = []
    in_quote = False
    quote_char = ''
    for ch in text:
        if in_quote:
            if ch == quote_char:
                in_quote = False
            else:
                current.append(ch)
        elif ch in ('"', "'"):
            in_quote = True
            quote_char = ch
        elif ch == ',':
            items.append(''.join(current).strip())
            current = []
        else:
            current.append(ch)
    items.append(''.join(current).strip())
    return [i for i in items if i is not None]   # keep empty strings as ''


def parse(line: str) -> Optional[DataTableDiagram]:
    # headers: [ColA, ColB, ...]
    hm = re.search(r'\bheaders:\s*\[([^\]]*)\]', line)
    if not hm:
        return None
    headers = [h.strip() for h in hm.group(1).split(',')]
    if not headers:
        return None
    n_cols = len(headers)

    # rows: [(val, val), (val, val), ...]
    rows: List[List[str]] = []
    rm = re.search(r'\brows:\s*\[', line)
    if rm:
        rows_str = line[rm.end():]
        for m in re.finditer(r'\(([^)]*)\)', rows_str):
            cells = _split_csv(m.group(1))
            while len(cells) < n_cols:
                cells.append('')
            rows.append(cells[:n_cols])

    if not rows:
        return None

    lc_m = re.search(r'\blabel_col:\s*(true|false)', line)
    label_col = bool(lc_m and lc_m.group(1) == 'true')

    return DataTableDiagram(headers=headers, rows=rows, label_col=label_col)


def _svg_label(text: str, x: float, y: float, fs: float, anchor: str, extra_attrs: str = '') -> str:
    """Render a label as SVG <text> with ^n / ^{n} superscript support (mirrors AlgebraTable)."""
    parts = re.split(r'\^\{([^}]*)\}|\^(-?[a-zA-Z0-9]+)', text)
    if len(parts) == 1:
        return (
            f'<text x="{x:.3f}" y="{y:.3f}" font-size="{fs:.3f}" '
            f'font-family="system-ui, -apple-system, sans-serif" '
            f'text-anchor="{anchor}" dominant-baseline="middle" {extra_attrs}>'
            f'{text}</text>'
        )
    sup_fs = fs * 0.72
    sup_dy = -fs * 0.48
    reset_dy = fs * 0.48
    spans = []
    i = 0
    while i < len(parts):
        chunk = parts[i]
        if chunk:
            dy_attr = '' if i == 0 else f' dy="{reset_dy:.3f}"'
            spans.append(f'<tspan{dy_attr}>{chunk}</tspan>')
        g1 = parts[i + 1] if i + 1 < len(parts) else None
        g2 = parts[i + 2] if i + 2 < len(parts) else None
        sup = g1 if g1 is not None else g2
        if sup is not None:
            spans.append(f'<tspan dy="{sup_dy:.3f}" font-size="{sup_fs:.3f}">{sup}</tspan>')
        i += 3
    return (
        f'<text x="{x:.3f}" y="{y:.3f}" font-size="{fs:.3f}" '
        f'font-family="system-ui, -apple-system, sans-serif" '
        f'text-anchor="{anchor}" dominant-baseline="middle" {extra_attrs}>'
        + ''.join(spans)
        + '</text>'
    )


def _compute_layout(d: DataTableDiagram):
    """Returns (total_w, label_w, data_w, font_size).

    Mirrors AlgebraTable: first column is 1.5× the width of the data columns so
    row-label text (e.g. "January", "Category A") fits without crowding.
    total_w = label_w + (n_cols - 1) * data_w = BASE_W always.
    """
    n_cols = len(d.headers)
    BASE_W = 56.0
    TARGET_FS = 2.16
    # Same formula as AlgebraTable (label col counts as 1.5 data cols)
    data_w = BASE_W / (0.5 + n_cols)
    label_w = 1.5 * data_w
    total_w = label_w + (n_cols - 1) * data_w
    font_size = min(data_w * 0.32, TARGET_FS)
    return total_w, label_w, data_w, font_size


def viewbox(d: DataTableDiagram) -> tuple:
    total_w, _, _, _ = _compute_layout(d)
    n_rows_total = 1 + len(d.rows)   # header row + data rows
    cell_h = 6.5
    total_h = cell_h * n_rows_total
    pad_x, pad_y = 2.0, 2.0
    return (
        -(total_w + 2 * pad_x) / 2,
        -(total_h + 2 * pad_y) / 2,
        total_w + 2 * pad_x,
        total_h + 2 * pad_y,
    )


def render(d: DataTableDiagram) -> str:
    n_cols = len(d.headers)
    n_rows_total = 1 + len(d.rows)
    total_w, label_w, data_w, font_size = _compute_layout(d)
    cell_h = 6.5
    total_h = cell_h * n_rows_total

    x0 = -total_w / 2
    y0 = -total_h / 2

    FILL_HEADER = "#e8e8e8"
    FILL_NORMAL = "#ffffff"
    STROKE = "#888888"
    SW = 0.15

    def col_x(col_idx: int) -> float:
        return x0 if col_idx == 0 else x0 + label_w + (col_idx - 1) * data_w

    def col_width(col_idx: int) -> float:
        return label_w if col_idx == 0 else data_w

    out = []

    # ── Cells ────────────────────────────────────────────────────────────────
    for row_idx in range(n_rows_total):
        is_header_row = row_idx == 0
        for col_idx in range(n_cols):
            cx = col_x(col_idx)
            cw = col_width(col_idx)
            cy = y0 + row_idx * cell_h

            is_first_col = col_idx == 0
            shaded = is_header_row or (is_first_col and d.label_col)
            fill = FILL_HEADER if shaded else FILL_NORMAL

            out.append(
                f'<rect x="{cx:.3f}" y="{cy:.3f}" '
                f'width="{cw:.3f}" height="{cell_h:.3f}" '
                f'fill="{fill}" stroke="none"/>'
            )

            # Cell text
            if is_header_row:
                text = d.headers[col_idx]
            else:
                dr = d.rows[row_idx - 1]
                text = dr[col_idx] if col_idx < len(dr) else ''

            if text:
                bold = shaded                  # bold in header row and label column
                if is_first_col:
                    tx = cx + cw * 0.08        # left-aligned with small indent
                    anchor = 'start'
                else:
                    tx = cx + cw / 2           # centred
                    anchor = 'middle'
                ty = cy + cell_h / 2
                extra = 'font-weight="bold"' if bold else ''
                out.append(_svg_label(text, tx, ty, font_size, anchor, extra))

    # ── Horizontal lines only (top, between each row, bottom) ─────────────
    for i in range(n_rows_total + 1):
        hy = y0 + i * cell_h
        out.append(
            f'<line x1="{x0:.3f}" y1="{hy:.3f}" x2="{x0 + total_w:.3f}" y2="{hy:.3f}" '
            f'stroke="{STROKE}" stroke-width="{SW}"/>'
        )

    return '\n'.join(out)
