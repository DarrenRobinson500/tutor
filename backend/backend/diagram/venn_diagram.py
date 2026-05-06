import re
import math
from dataclasses import dataclass, field
from typing import List, Optional, Tuple

DIAGRAM_TYPE = "VennDiagram"
SUPPORTS_VIZ_SCALE = True

# Syntax:
#   VennDiagram(
#     label_A: "Sport", label_B: "Music",
#     only_A: 12, both: 5, only_B: 8, neither: 3,
#     total: 28,
#     highlight: "both",
#     show_labels: true,
#     label_box: "Students",
#     pos: (0, 0)
#   )
#
# highlight — one of: "only_A", "both", "only_B", "neither", "A", "B", or ""
# show_labels — false (default): show counts only
#               true: show "X only", "Both", "Neither" below counts
# label_box — optional top-left label for the bounding rectangle
# total — optional; if provided and does not match only_A+both+only_B+neither,
#          a warning badge is shown in the corner

_FONT = "system-ui, -apple-system, sans-serif"

# Geometry (SVG units, at viz_scale=1.0)
_CX_A   = -7.0   # centre x of circle A
_CX_B   =  7.0   # centre x of circle B
_CY     =  0.0   # centre y of both circles
_R      = 10.5   # radius
_BOX_W  = 50.0
_BOX_H  = 28.0

# Colours
_C_FILL    = "#ffffff"
_C_STROKE  = "#374151"
_C_HL_FILL = "#E6F1FB"
_C_HL_STR  = "#185FA5"
_C_HL_TXT  = "#0C447C"
_C_TEXT    = "#374151"
_C_MUTED   = "#9ca3af"
_C_WARN    = "#dc2626"
_C_BOX_BG  = "#f9fafb"


@dataclass
class VennDiagramData:
    label_A:     str   = "A"
    label_B:     str   = "B"
    only_A:      Optional[str] = None
    both:        Optional[str] = None
    only_B:      Optional[str] = None
    neither:     Optional[str] = None
    total:       Optional[str] = None
    highlight:   List[str] = field(default_factory=list)
    show_labels: bool  = False
    label_box:   str   = ""
    pos:         Tuple[float, float] = (0.0, 0.0)


# ── Parsing ────────────────────────────────────────────────────────────────────

def _parse_highlight(line: str) -> List[str]:
    """Parse highlight: ["a", "b"] or highlight: "a" (single-value backwards compat)."""
    m = re.search(r'\bhighlight:\s*\[([^\]]*)\]', line)
    if m:
        return [s.strip().strip('"\'').lower() for s in m.group(1).split(',')
                if s.strip().strip('"\'')]
    m = re.search(r'\bhighlight:\s*"([^"]*)"', line)
    if m and m.group(1).strip():
        return [m.group(1).strip().lower()]
    return []


def _get_str(line: str, key: str) -> Optional[str]:
    """Extract a quoted or bare value for `key:` from the line."""
    m = re.search(rf'\b{re.escape(key)}:\s*"([^"]*)"', line)
    if m:
        return m.group(1)
    m = re.search(rf'\b{re.escape(key)}:\s*([^,)\s]+)', line)
    return m.group(1) if m else None


def _get_bool(line: str, key: str) -> Optional[bool]:
    m = re.search(rf'\b{re.escape(key)}:\s*(true|false)', line)
    if not m:
        return None
    return m.group(1) == "true"


def parse(line: str) -> Optional[VennDiagramData]:
    if not line.startswith("VennDiagram"):
        return None

    d = VennDiagramData()

    label_A = _get_str(line, "label_A")
    if label_A is not None:
        d.label_A = label_A

    label_B = _get_str(line, "label_B")
    if label_B is not None:
        d.label_B = label_B

    d.only_A   = _get_str(line, "only_A")
    d.both     = _get_str(line, "both")
    d.only_B   = _get_str(line, "only_B")
    d.neither  = _get_str(line, "neither")
    d.total    = _get_str(line, "total")

    d.highlight = _parse_highlight(line)

    sl = _get_bool(line, "show_labels")
    if sl is not None:
        d.show_labels = sl

    lb = _get_str(line, "label_box")
    if lb is not None:
        d.label_box = lb

    pos_m = re.search(r'\bpos:\s*\(\s*(-?[\d.]+)\s*,\s*(-?[\d.]+)\s*\)', line)
    if pos_m:
        d.pos = (float(pos_m.group(1)), float(pos_m.group(2)))

    return d


# ── Geometry helpers ───────────────────────────────────────────────────────────

def _circle_intersection_x(cx_a: float, cx_b: float, r: float) -> float:
    """X coordinate of the two circle-circle intersection points."""
    d = cx_b - cx_a
    return cx_a + (d / 2)


def _lens_path(cx_a: float, cx_b: float, cy: float, r: float) -> str:
    """SVG path for the lens (vesica) shaped overlap of two equal circles."""
    d = abs(cx_b - cx_a)
    # Half-chord height at intersection x
    h = math.sqrt(max(0.0, r * r - (d / 2) ** 2))
    ix = (cx_a + cx_b) / 2
    iy_top = cy - h
    iy_bot = cy + h
    # Arc from top intersection to bottom intersection along circle A,
    # then arc back along circle B.
    # Arc A sweeps clockwise (large-arc=0, sweep=1) from top to bottom
    # Arc B sweeps clockwise (large-arc=0, sweep=1) from bottom to top
    return (
        f"M {ix:.4f},{iy_top:.4f} "
        f"A {r:.4f},{r:.4f} 0 0,1 {ix:.4f},{iy_bot:.4f} "
        f"A {r:.4f},{r:.4f} 0 0,1 {ix:.4f},{iy_top:.4f} Z"
    )



# ── viewbox ────────────────────────────────────────────────────────────────────

def viewbox(d: VennDiagramData) -> tuple:
    pad = 3.0
    w = _BOX_W + 2 * pad
    h = _BOX_H + 2 * pad
    ox, oy = d.pos
    return (ox - w / 2, oy - h / 2, w, h)


# ── render ─────────────────────────────────────────────────────────────────────

def render(d: VennDiagramData, viz_scale: float = 1.0) -> str:
    ox, oy = d.pos

    fs      = 2.2 * viz_scale
    fs_sm   = 1.7 * viz_scale
    fs_lbl  = 1.8 * viz_scale
    sw      = 0.35 * viz_scale
    sw_hl   = 0.55 * viz_scale

    half_w = _BOX_W / 2
    half_h = _BOX_H / 2

    # Absolute circle centres / radius
    cx_a = ox + _CX_A
    cx_b = ox + _CX_B
    cy   = oy + _CY
    r    = _R

    hl_set = set(d.highlight)   # already lowercase from parse()

    # "a" / "b" shade the entire circle (crescent + lens).
    # "only_a" / "only_b" shade only the crescent.
    # Both cases fill the full circle first; the lens is then erased or re-filled.
    hl_only_a  = bool({"only_a", "a"} & hl_set)
    hl_both    = bool({"both",   "a", "b"} & hl_set)
    hl_only_b  = bool({"only_b", "b"} & hl_set)
    hl_neither = "neither" in hl_set

    out: List[str] = []

    # ── Universal set rectangle ───────────────────────────────────────────────
    rx = ox - half_w
    ry = oy - half_h
    out.append(
        f'<rect x="{rx:.3f}" y="{ry:.3f}" '
        f'width="{_BOX_W:.3f}" height="{_BOX_H:.3f}" '
        f'rx="2" ry="2" '
        f'fill="{_C_BOX_BG}" stroke="{_C_STROKE}" stroke-width="{sw:.3f}"/>'
    )

    # ── Neither region highlight ──────────────────────────────────────────────
    # (rendered before circles so it sits underneath)
    if hl_neither:
        out.append(
            f'<rect x="{rx:.3f}" y="{ry:.3f}" '
            f'width="{_BOX_W:.3f}" height="{_BOX_H:.3f}" '
            f'rx="2" ry="2" '
            f'fill="{_C_HL_FILL}" stroke="none"/>'
        )

    # ── White circles (background) ────────────────────────────────────────────
    out.append(
        f'<circle cx="{cx_a:.3f}" cy="{cy:.3f}" r="{r:.3f}" '
        f'fill="{_C_FILL}" stroke="none"/>'
    )
    out.append(
        f'<circle cx="{cx_b:.3f}" cy="{cy:.3f}" r="{r:.3f}" '
        f'fill="{_C_FILL}" stroke="none"/>'
    )

    # ── Region highlight fills ────────────────────────────────────────────────
    # Strategy: fill the full circle(s) first, then erase or re-paint the lens.
    # This avoids unreliable SVG crescent paths whose arc direction is ambiguous
    # when both circles share the same radius and intersection points.
    if hl_only_a:
        out.append(
            f'<circle cx="{cx_a:.3f}" cy="{cy:.3f}" r="{r:.3f}" '
            f'fill="{_C_HL_FILL}" stroke="none"/>'
        )
    if hl_only_b:
        out.append(
            f'<circle cx="{cx_b:.3f}" cy="{cy:.3f}" r="{r:.3f}" '
            f'fill="{_C_HL_FILL}" stroke="none"/>'
        )
    # Lens: erase (white) if the circles were filled but the overlap should NOT be
    # highlighted; paint (highlight) if the overlap itself is in the highlight set.
    if hl_both:
        out.append(
            f'<path d="{_lens_path(cx_a, cx_b, cy, r)}" '
            f'fill="{_C_HL_FILL}" stroke="none"/>'
        )
    elif hl_only_a or hl_only_b:
        out.append(
            f'<path d="{_lens_path(cx_a, cx_b, cy, r)}" '
            f'fill="{_C_FILL}" stroke="none"/>'
        )

    # ── Circle outlines ───────────────────────────────────────────────────────
    stroke_a = _C_HL_STR if hl_only_a else _C_STROKE
    stroke_b = _C_HL_STR if hl_only_b else _C_STROKE
    sw_a = sw_hl if hl_only_a else sw
    sw_b = sw_hl if hl_only_b else sw

    out.append(
        f'<circle cx="{cx_a:.3f}" cy="{cy:.3f}" r="{r:.3f}" '
        f'fill="none" stroke="{stroke_a}" stroke-width="{sw_a:.3f}"/>'
    )
    out.append(
        f'<circle cx="{cx_b:.3f}" cy="{cy:.3f}" r="{r:.3f}" '
        f'fill="none" stroke="{stroke_b}" stroke-width="{sw_b:.3f}"/>'
    )

    # ── Highlighted lens outline ──────────────────────────────────────────────
    if hl_both:
        out.append(
            f'<path d="{_lens_path(cx_a, cx_b, cy, r)}" '
            f'fill="none" stroke="{_C_HL_STR}" stroke-width="{sw_hl:.3f}"/>'
        )

    # ── Circle labels (centred above each circle) ────────────────────────────
    lbl_y = cy - r - fs_lbl * 0.8 * viz_scale
    tc_a = _C_HL_TXT if hl_only_a else _C_TEXT
    tc_b = _C_HL_TXT if hl_only_b else _C_TEXT

    out.append(
        f'<text x="{cx_a:.3f}" y="{lbl_y:.3f}" '
        f'font-size="{fs_lbl:.3f}" font-family="{_FONT}" '
        f'fill="{tc_a}" '
        f'text-anchor="middle" dominant-baseline="middle">'
        f'{d.label_A}</text>'
    )
    out.append(
        f'<text x="{cx_b:.3f}" y="{lbl_y:.3f}" '
        f'font-size="{fs_lbl:.3f}" font-family="{_FONT}" '
        f'fill="{tc_b}" '
        f'text-anchor="middle" dominant-baseline="middle">'
        f'{d.label_B}</text>'
    )

    # ── Region count labels ───────────────────────────────────────────────────
    ix = (cx_a + cx_b) / 2   # intersection x midpoint

    # Vertical centres for count and sub-label
    count_y    = cy - fs_sm * 0.4 * viz_scale if d.show_labels else cy
    sublbl_y   = cy + fs * 1.1 * viz_scale

    def _count_text(val, x, y, is_hl, anchor="middle"):
        if val is None:
            return ""
        tc = _C_HL_TXT if is_hl else _C_TEXT
        return (
            f'<text x="{x:.3f}" y="{y:.3f}" '
            f'font-size="{fs:.3f}" font-family="{_FONT}" '
            f'fill="{tc}" font-weight="bold" '
            f'text-anchor="{anchor}" dominant-baseline="middle">'
            f'{val}</text>'
        )

    def _sub_text(label, x, y, is_hl, anchor="middle"):
        tc = _C_HL_TXT if is_hl else _C_MUTED
        return (
            f'<text x="{x:.3f}" y="{y:.3f}" '
            f'font-size="{fs_sm:.3f}" font-family="{_FONT}" '
            f'fill="{tc}" '
            f'text-anchor="{anchor}" dominant-baseline="middle">'
            f'{label}</text>'
        )

    # only_A count — centred in left crescent
    only_a_x = (cx_a - r + ix) / 2
    out.append(_count_text(d.only_A, only_a_x, count_y, hl_only_a))
    if d.show_labels and d.only_A is not None:
        only_a_lbl = f"{d.label_A} only"
        out.append(_sub_text(only_a_lbl, only_a_x, sublbl_y, hl_only_a))

    # both count — centred in lens
    out.append(_count_text(d.both, ix, count_y, hl_both))
    if d.show_labels and d.both is not None:
        out.append(_sub_text("Both", ix, sublbl_y, hl_both))

    # only_B count — centred in right crescent
    only_b_x = (ix + cx_b + r) / 2
    out.append(_count_text(d.only_B, only_b_x, count_y, hl_only_b))
    if d.show_labels and d.only_B is not None:
        only_b_lbl = f"{d.label_B} only"
        out.append(_sub_text(only_b_lbl, only_b_x, sublbl_y, hl_only_b))

    # neither count — bottom-right corner of the rectangle
    neither_x = ox + half_w - 3.0 * viz_scale
    neither_y = oy + half_h - 2.5 * viz_scale
    out.append(_count_text(d.neither, neither_x, neither_y, hl_neither, anchor="end"))
    if d.show_labels and d.neither is not None:
        out.append(_sub_text("Neither", neither_x, neither_y - fs * 1.2 * viz_scale, hl_neither, anchor="end"))

    # ── label_box (top-left corner label) ────────────────────────────────────
    if d.label_box:
        lbx = ox - half_w + 1.5 * viz_scale
        lby = oy - half_h + 1.5 * viz_scale
        out.append(
            f'<text x="{lbx:.3f}" y="{lby:.3f}" '
            f'font-size="{fs_sm:.3f}" font-family="{_FONT}" '
            f'fill="{_C_MUTED}" '
            f'text-anchor="start" dominant-baseline="hanging">'
            f'{d.label_box}</text>'
        )

    # ── Total mismatch warning ────────────────────────────────────────────────
    if d.total is not None:
        try:
            expected = int(d.total)
            parts = [d.only_A, d.both, d.only_B, d.neither]
            if all(p is not None for p in parts):
                actual = sum(int(p) for p in parts)
                if actual != expected:
                    wx = ox + half_w - 1.5 * viz_scale
                    wy = oy - half_h + 1.5 * viz_scale
                    out.append(
                        f'<text x="{wx:.3f}" y="{wy:.3f}" '
                        f'font-size="{fs_sm:.3f}" font-family="{_FONT}" '
                        f'fill="{_C_WARN}" font-weight="bold" '
                        f'text-anchor="end" dominant-baseline="hanging">'
                        f'⚠ {actual}≠{expected}</text>'
                    )
        except (TypeError, ValueError):
            pass

    return "\n".join(s for s in out if s)
