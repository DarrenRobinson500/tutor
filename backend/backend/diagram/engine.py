import re
from typing import List

from . import DIAGRAM_REGISTRY


# ── Auto-zoom helpers ─────────────────────────────────────────────────────────

def _attr_float(attrs: str, name: str, default: float = 0.0) -> float:
    """Extract a numeric attribute value from a fragment of SVG tag attributes."""
    m = re.search(rf'\b{name}="(-?[\d.e+-]+)"', attrs)
    return float(m.group(1)) if m else default


def _svg_content_bbox(svg_body: str):
    """
    Estimate the bounding box of rendered SVG content by scanning common element
    coordinate attributes.  Returns (x_min, y_min, x_max, y_max) or None.
    <text> elements are excluded (font metrics are unavailable here).
    <path> M/L commands are included as approximate anchor points.
    """
    xs, ys = [], []

    # <rect x y width height>
    for m in re.finditer(r'<rect\b([^>]*)>', svg_body):
        t = m.group(1)
        x = _attr_float(t, 'x');  y = _attr_float(t, 'y')
        xs += [x, x + _attr_float(t, 'width')]
        ys += [y, y + _attr_float(t, 'height')]

    # <circle cx cy r>
    for m in re.finditer(r'<circle\b([^>]*)>', svg_body):
        t = m.group(1)
        cx = _attr_float(t, 'cx');  cy = _attr_float(t, 'cy');  r = _attr_float(t, 'r')
        xs += [cx - r, cx + r];  ys += [cy - r, cy + r]

    # <ellipse cx cy rx ry>
    for m in re.finditer(r'<ellipse\b([^>]*)>', svg_body):
        t = m.group(1)
        cx = _attr_float(t, 'cx');  cy = _attr_float(t, 'cy')
        xs += [cx - _attr_float(t, 'rx'), cx + _attr_float(t, 'rx')]
        ys += [cy - _attr_float(t, 'ry'), cy + _attr_float(t, 'ry')]

    # <line x1 y1 x2 y2>
    for m in re.finditer(r'<line\b([^>]*)>', svg_body):
        t = m.group(1)
        xs += [_attr_float(t, 'x1'), _attr_float(t, 'x2')]
        ys += [_attr_float(t, 'y1'), _attr_float(t, 'y2')]

    # <polygon points="x1,y1 x2,y2 ..."> and <polyline>
    for m in re.finditer(r'<(?:polygon|polyline)\b[^>]*points="([^"]*)"', svg_body):
        for px, py in re.findall(r'(-?[\d.]+),\s*(-?[\d.]+)', m.group(1)):
            xs.append(float(px));  ys.append(float(py))

    # <path d="...">: extract absolute M and L anchor coordinates
    for m in re.finditer(r'<path\b[^>]*\bd="([^"]*)"', svg_body):
        for px, py in re.findall(r'[ML]\s*(-?[\d.]+)[,\s]+(-?[\d.]+)', m.group(1)):
            xs.append(float(px));  ys.append(float(py))

    # <text x y font-size>: estimate extent based on anchor direction.
    # Use 5× font-size as an approximate text width (covers "deg = N" and similar
    # multi-character labels); direction depends on text-anchor attribute.
    for m in re.finditer(r'<text\b([^>]*)>', svg_body):
        t = m.group(1)
        tx = _attr_float(t, 'x');  ty = _attr_float(t, 'y')
        fs = _attr_float(t, 'font-size', 2.0)
        tw = fs * 5.0
        am = re.search(r'text-anchor="(\w+)"', t)
        anchor = am.group(1) if am else 'start'
        if anchor == 'middle':
            xs += [tx - tw / 2, tx + tw / 2]
        elif anchor == 'end':
            xs += [tx - tw, tx]
        else:
            xs += [tx, tx + tw]
        ys += [ty - fs, ty + fs]

    if not xs or not ys:
        return None
    return min(xs), min(ys), max(xs), max(ys)


def _auto_zoom_viewbox(vb, svg_body: str, min_width_ratio: float = 0.6, min_height_ratio: float = 0.9):
    """
    Adjust the viewBox in both directions:
    - Zoom in  (shrink) when content fills less than min_width_ratio / min_height_ratio.
    - Zoom out (expand) when content overflows (fills more than max_ratio in either dimension).

    The original aspect ratio is preserved and the viewBox is centred on the content.
    Returns the original vb unchanged if no adjustment is needed or possible.
    """
    MAX_RATIO = 0.92   # content must not exceed this fraction of the viewBox

    vb_min_x, vb_min_y, vb_w, vb_h = vb
    if vb_w <= 0 or vb_h <= 0:
        return vb

    bbox = _svg_content_bbox(svg_body)
    if bbox is None:
        return vb

    cx_min, cy_min, cx_max, cy_max = bbox
    content_w = cx_max - cx_min
    content_h = cy_max - cy_min
    if content_w <= 0 or content_h <= 0:
        return vb

    # ── Zoom-out target: smallest viewBox where content fits within MAX_RATIO ──
    vb_w_to_fit = max(
        content_w / MAX_RATIO,
        (content_h / MAX_RATIO) * (vb_w / vb_h),
    )

    # ── Zoom-in target: smallest viewBox where content fills min ratios ────────
    vb_w_to_fill = max(
        content_w / min_width_ratio,
        (content_h / min_height_ratio) * (vb_w / vb_h),
    )

    if vb_w_to_fit > vb_w:
        # Content overflows — expand viewBox
        new_vb_w = vb_w_to_fit
    elif vb_w_to_fill < vb_w:
        # Content too small — shrink viewBox
        new_vb_w = vb_w_to_fill
    else:
        new_vb_w = vb_w

    # Trim height independently to content — eliminates dead vertical space
    # for wide/short diagrams (e.g. NumberLine) without affecting the width zoom.
    new_vb_h = content_h / MAX_RATIO

    # Centre each axis on the content independently
    cx_center = (cx_min + cx_max) / 2
    cy_center = (cy_min + cy_max) / 2
    new_vb_min_x = cx_center - new_vb_w / 2
    new_vb_min_y = cy_center - new_vb_h / 2

    return new_vb_min_x, new_vb_min_y, new_vb_w, new_vb_h


# ─────────────────────────────────────────────────────────────────────────────

def _split_diagram_code(code: str) -> List[str]:
    """Split a diagram code string into individual diagram specs.

    Splits on newlines, semicolons, and top-level commas (commas not inside
    any parentheses), so that:
      FractionBar(a: 3, den: 12), FractionBar(a: 4, den: 12)
    is treated as two separate diagrams.
    """
    segments = []
    current = []
    depth = 0
    for ch in code:
        if depth == 0 and ch in '\n;,':
            segment = ''.join(current).strip()
            if segment:
                segments.append(segment)
            current = []
        else:
            if ch == '(':
                depth += 1
            elif ch == ')':
                depth -= 1
            current.append(ch)
    segment = ''.join(current).strip()
    if segment:
        segments.append(segment)
    return segments


def render_diagram_from_code(code: str, width: int = 500) -> str:
    if not code:
        return ""
    if not isinstance(code, str):
        return ""
    if not code.strip():
        return ""

    # Collapse any embedded newlines + surrounding whitespace within each
    # segment into a single space.  This handles YAML `>` folded block scalars
    # whose continuation lines are more-indented than the first line, causing
    # PyYAML to preserve literal newlines inside the diagram call string.
    lines = [re.sub(r'\s*\n\s*', ' ', s) for s in _split_diagram_code(code)]

    DEFAULT_VIEWBOX = (-30, -18, 60, 36)

    # ── Parse all diagram lines first ────────────────────────────────────────
    items = []   # list of (module, parsed)
    errors = []  # human-readable error strings
    vb = DEFAULT_VIEWBOX
    for line in lines:
        matched = False
        for diagram_type, module in sorted(DIAGRAM_REGISTRY.items(), key=lambda x: -len(x[0])):
            if line.startswith(diagram_type):
                matched = True
                try:
                    parsed = module.parse(line)
                    if parsed:
                        items.append((module, parsed))
                        if hasattr(module, "viewbox"):
                            vb = module.viewbox(parsed)
                    else:
                        errors.append(f"Could not parse: {line}")
                except Exception as e:
                    errors.append(str(e))
                break
        if not matched:
            errors.append(f"Unknown diagram type: {line.split('(')[0]}")

    if not items and errors:
        # Nothing rendered — show the error message inside the SVG
        msg = " | ".join(errors)
        # font-size 2.5 SVG units ≈ 1.4 units/char; viewBox width 60 → ~38 chars fit
        font_size = 2.5
        wrap_chars = 36
        words = msg.split()
        lines_out, cur = [], ""
        for w in words:
            if len(cur) + len(w) + 1 > wrap_chars:
                lines_out.append(cur)
                cur = w
            else:
                cur = (cur + " " + w).strip()
        if cur:
            lines_out.append(cur)
        line_h = 3.5
        total_h = max(20, len(lines_out) * line_h + 8)
        vb_str = f"-30 -{total_h/2} 60 {total_h}"
        text_els = "".join(
            f'<text x="0" y="{-((len(lines_out)-1)*line_h/2) + i*line_h:.1f}" '
            f'font-size="{font_size}" font-family="system-ui,sans-serif" fill="#c00" '
            f'text-anchor="middle" dominant-baseline="middle">{l}</text>'
            for i, l in enumerate(lines_out)
        )
        return (
            f'<svg width="500" height="{round(500*total_h/60)}" '
            f'viewBox="{vb_str}" xmlns="http://www.w3.org/2000/svg">'
            f'<rect x="-30" y="-{total_h/2}" width="60" height="{total_h}" '
            f'fill="#fff8f8" stroke="#c00" stroke-width="0.4" rx="1"/>'
            f'{text_els}</svg>'
        )

    # ── HTML modules bypass the SVG pipeline entirely ────────────────────────
    for module, parsed in items:
        if getattr(module, 'RENDERS_HTML', False):
            return module.render(parsed)

    def _render(module, parsed, viz_scale):
        """Render one diagram, passing viz_scale if the module supports it."""
        if getattr(module, 'SUPPORTS_VIZ_SCALE', False):
            return module.render(parsed, viz_scale=viz_scale)
        return module.render(parsed)

    # ── Pass 1: render at natural scale (viz_scale=1.0) to get combined bbox ─
    body1 = "\n".join(_render(m, p, 1.0) for m, p in items)
    vb1 = _auto_zoom_viewbox(vb, body1, min_width_ratio=0.9, min_height_ratio=0.9)

    # Derive the global viz_scale from the combined viewBox width
    global_viz_scale = vb1[2] / DEFAULT_VIEWBOX[2]   # final_vw / 60.0

    # ── Pass 2: render with globally-consistent viz_scale ────────────────────
    body = "\n".join(_render(m, p, global_viz_scale) for m, p in items)
    vb = _auto_zoom_viewbox(vb, body, min_width_ratio=0.9, min_height_ratio=0.9)

    vb_min_x, vb_min_y, vb_w, vb_h = vb
    svg_w = width
    svg_h = round(svg_w * vb_h / vb_w)
    vb_str = f"{vb_min_x} {vb_min_y} {vb_w} {vb_h}"

    pre = f'<svg width="{svg_w}" height="{svg_h}" viewBox="{vb_str}" xmlns="http://www.w3.org/2000/svg">'
    post = '</svg>'

    return pre + str(body) + post