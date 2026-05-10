import re
from dataclasses import dataclass, field
from typing import List, Optional, Tuple

DIAGRAM_TYPE = "DataTable"
SUPPORTS_VIZ_SCALE = True

# Syntax:
#   DataTable(headers: [Month, Rainfall], rows: [(Jan, 45), (Feb, 62), (Mar, 38)])
#   DataTable(headers: [, 2020, 2021, 2022], rows: [(Pop, 45, 52, 61)], label_col: true)
#
# label_col: true  — shades the first data column grey as well as the header row,
#                    making it act as a row-header column.

_FONT   = "system-ui, -apple-system, sans-serif"
_CHAR_W = 0.58          # estimated (char width) / font_size for system-ui
TARGET_FS  = 2.0        # font size in SVG units at viz_scale = 1.0
_CELL_H    = 6.5        # data row height at viz_scale = 1.0
_PAD_SCALE = 1.0        # vertical padding inside a cell, in multiples of font_size


_C_HL       = "#dbeafe"   # highlight fill (light blue)
_C_HL_LABEL = "#bfdbfe"   # slightly darker for label-column cells in a highlighted row


@dataclass
class DataTableDiagram:
    headers:   List[str]       = field(default_factory=list)
    rows:      List[List[str]] = field(default_factory=list)
    label_col: bool            = False
    highlight: List[str]       = field(default_factory=list)  # e.g. ["row_1", "row_2"]


# ── Parsing ───────────────────────────────────────────────────────────────────

def _split_csv(text: str) -> List[str]:
    items: List[str] = []
    current: List[str] = []
    in_quote = False
    quote_char = ''
    i = 0
    while i < len(text):
        ch = text[i]
        if in_quote:
            if ch == quote_char:
                in_quote = False
            else:
                current.append(ch)
        elif ch in ('"', "'"):
            in_quote = True
            quote_char = ch
        elif ch == ',':
            # Treat as a thousands separator (not a cell delimiter) when:
            #   - the character before the comma is a digit, AND
            #   - the next exactly 3 characters are all digits, AND
            #   - the character after those 3 digits is a non-digit (or end of string)
            # This correctly handles $40,000 and $1,000,000 inside cell values.
            before_digit = bool(current) and current[-1].isdigit()
            after3 = text[i + 1 : i + 4]
            after_is_thousands = (
                before_digit
                and len(after3) == 3
                and after3.isdigit()
                and (i + 4 >= len(text) or not text[i + 4].isdigit())
            )
            if after_is_thousands:
                current.append(ch)
            else:
                items.append(''.join(current).strip())
                current = []
        else:
            current.append(ch)
        i += 1
    items.append(''.join(current).strip())
    return [item for item in items if item is not None]


def parse(line: str) -> Optional[DataTableDiagram]:
    hm = re.search(r'\bheaders:\s*\[([^\]]*)\]', line)
    if not hm:
        return None
    headers = [h.strip() for h in hm.group(1).split(',')]
    if not headers:
        return None
    n_cols = len(headers)

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

    hl_m = re.search(r'\bhighlight:\s*\[([^\]]*)\]', line)
    if hl_m:
        highlight = [s.strip().strip('"\'') for s in hl_m.group(1).split(',') if s.strip()]
    else:
        highlight = []

    return DataTableDiagram(headers=headers, rows=rows, label_col=label_col, highlight=highlight)


# ── Text helpers ──────────────────────────────────────────────────────────────

def _wrap(text: str, col_w: float, fs: float) -> List[str]:
    """Word-wrap text to fit within col_w SVG units."""
    if not text:
        return []
    max_chars = max(4, int(col_w / (fs * _CHAR_W)))
    words = text.split()
    if not words:
        return []
    lines: List[str] = []
    cur = words[0]
    for w in words[1:]:
        if len(cur) + 1 + len(w) <= max_chars:
            cur += ' ' + w
        else:
            lines.append(cur)
            cur = w
    lines.append(cur)
    return lines


def _svg_text_lines(lines: List[str], x: float, cy: float, fs: float,
                    anchor: str, extra: str = '') -> str:
    """Render pre-wrapped lines centred vertically on cy."""
    if not lines:
        return ''
    lh = fs * 1.5
    y0 = cy - (len(lines) - 1) * lh / 2
    parts = []
    for i, ln in enumerate(lines):
        parts.append(
            f'<text x="{x:.3f}" y="{y0 + i * lh:.3f}" font-size="{fs:.3f}" '
            f'font-family="{_FONT}" text-anchor="{anchor}" '
            f'dominant-baseline="middle" {extra}>{ln}</text>'
        )
    return '\n'.join(parts)


def _svg_label(text: str, x: float, y: float, fs: float,
               anchor: str, extra: str = '') -> str:
    """Single-line label with ^n / ^{n} superscript support."""
    parts = re.split(r'\^\{([^}]*)\}|\^(-?[a-zA-Z0-9]+)', text)
    if len(parts) == 1:
        return (
            f'<text x="{x:.3f}" y="{y:.3f}" font-size="{fs:.3f}" '
            f'font-family="{_FONT}" text-anchor="{anchor}" '
            f'dominant-baseline="middle" {extra}>{text}</text>'
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
        f'font-family="{_FONT}" text-anchor="{anchor}" '
        f'dominant-baseline="middle" {extra}>'
        + ''.join(spans) + '</text>'
    )


# ── Layout ────────────────────────────────────────────────────────────────────

def _compute_layout(d: DataTableDiagram, viz_scale: float = 1.0):
    """Return (total_w, label_w, data_w, fs, header_h, cell_h)."""
    n_cols   = len(d.headers)
    BASE_W   = 56.0 * viz_scale
    # Font size is fixed in SVG units regardless of viz_scale so it stays
    # visually consistent when the engine auto-zooms the viewBox.
    fs       = TARGET_FS
    data_w   = BASE_W / (0.5 + n_cols)
    label_w  = 1.5 * data_w
    total_w  = label_w + (n_cols - 1) * data_w

    lh = fs * 1.5   # line height

    # Dynamic header height: enough for the most-wrapped header cell
    max_hdr_lines = 1
    for i, h in enumerate(d.headers):
        cw = label_w if i == 0 else data_w
        max_hdr_lines = max(max_hdr_lines, len(_wrap(h, cw, fs)))
    header_h = max(_CELL_H * viz_scale, max_hdr_lines * lh + fs * _PAD_SCALE)

    # Dynamic data-row height: enough for the most-wrapped label-column cell
    cell_h = _CELL_H * viz_scale
    if d.label_col:
        max_row_lines = 1
        for row in d.rows:
            if row:
                max_row_lines = max(max_row_lines, len(_wrap(row[0], label_w, fs)))
        cell_h = max(cell_h, max_row_lines * lh + fs * _PAD_SCALE)

    return total_w, label_w, data_w, fs, header_h, cell_h


def viewbox(d: DataTableDiagram) -> tuple:
    total_w, _, _, _, header_h, cell_h = _compute_layout(d)
    total_h = header_h + len(d.rows) * cell_h
    pad_x, pad_y = 2.0, 2.0
    return (
        -(total_w + 2 * pad_x) / 2,
        -(total_h + 2 * pad_y) / 2,
        total_w + 2 * pad_x,
        total_h + 2 * pad_y,
    )


# ── Render ────────────────────────────────────────────────────────────────────

def render(d: DataTableDiagram, viz_scale: float = 1.0) -> str:
    n_cols = len(d.headers)
    total_w, label_w, data_w, fs, header_h, cell_h = _compute_layout(d, viz_scale)
    total_h = header_h + len(d.rows) * cell_h

    x0 = -total_w / 2
    y0 = -total_h / 2

    FILL_HEADER = "#e8e8e8"
    FILL_NORMAL = "#ffffff"
    STROKE      = "#888888"
    SW          = 0.15

    # Build set of highlighted data row indices (1-indexed; 0 = header in the loop)
    hl_rows: set = set()
    for tok in d.highlight:
        m = re.match(r'^row_(\d+)$', tok.strip())
        if m:
            hl_rows.add(int(m.group(1)))

    def col_x(col_idx: int) -> float:
        return x0 if col_idx == 0 else x0 + label_w + (col_idx - 1) * data_w

    def col_width(col_idx: int) -> float:
        return label_w if col_idx == 0 else data_w

    def row_y(row_idx: int) -> float:
        return y0 if row_idx == 0 else y0 + header_h + (row_idx - 1) * cell_h

    def row_height(row_idx: int) -> float:
        return header_h if row_idx == 0 else cell_h

    n_rows_total = 1 + len(d.rows)
    out = []

    # ── Cells ─────────────────────────────────────────────────────────────────
    for row_idx in range(n_rows_total):
        is_header_row = row_idx == 0
        for col_idx in range(n_cols):
            cx  = col_x(col_idx)
            cw  = col_width(col_idx)
            cy  = row_y(row_idx)
            ch  = row_height(row_idx)
            is_first_col = col_idx == 0
            is_hl_row = (not is_header_row) and (row_idx in hl_rows)

            if is_hl_row:
                # Highlighted row: slightly deeper shade on the label column for contrast
                fill = _C_HL_LABEL if (is_first_col and d.label_col) else _C_HL
            elif is_header_row or (is_first_col and d.label_col):
                fill = FILL_HEADER
            else:
                fill = FILL_NORMAL

            shaded = is_header_row or (is_first_col and d.label_col)

            out.append(
                f'<rect x="{cx:.3f}" y="{cy:.3f}" '
                f'width="{cw:.3f}" height="{ch:.3f}" '
                f'fill="{fill}" stroke="none"/>'
            )

            text = d.headers[col_idx] if is_header_row else (
                d.rows[row_idx - 1][col_idx] if col_idx < len(d.rows[row_idx - 1]) else ''
            )
            # SVG text is not processed by KaTeX, so strip LaTeX escapes.
            text = text.replace('\\$', '$')

            if not text:
                continue

            bold  = shaded
            extra = 'font-weight="bold"' if bold else ''
            ty    = cy + ch / 2          # vertical centre of cell

            if is_first_col:
                tx     = cx + cw * 0.06
                anchor = 'start'
            else:
                tx     = cx + cw / 2
                anchor = 'middle'

            # Headers and label-column cells: word-wrap
            if is_header_row or (is_first_col and d.label_col):
                lines = _wrap(text, cw * 0.92, fs)
                out.append(_svg_text_lines(lines, tx, ty, fs, anchor, extra))
            else:
                out.append(_svg_label(text, tx, ty, fs, anchor, extra))

    # ── Horizontal grid lines ─────────────────────────────────────────────────
    for i in range(n_rows_total + 1):
        if i == 0:
            hy = y0
        elif i == 1:
            hy = y0 + header_h
        else:
            hy = y0 + header_h + (i - 1) * cell_h
        out.append(
            f'<line x1="{x0:.3f}" y1="{hy:.3f}" '
            f'x2="{x0 + total_w:.3f}" y2="{hy:.3f}" '
            f'stroke="{STROKE}" stroke-width="{SW}"/>'
        )

    return '\n'.join(s for s in out if s)
