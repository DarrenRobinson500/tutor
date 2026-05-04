import re
import math
from dataclasses import dataclass, field
from typing import List, Optional

DIAGRAM_TYPE = "Cylinder"
SUPPORTS_VIZ_SCALE = True

# Syntax: Cylinder(r: 5, h: 10, label_r: "5", label_h: "10")
# r:        radius of the circular cross-section
# h:        height of the cylinder
# labels:   true  →  auto-formatted numeric labels for r and h
# label_r:  custom label for the radius line on the top ellipse
# label_h:  custom label for the height (on the right side)
# pos: (x, y)   centre offset
# scale: N       scale factor
#
# The cylinder is drawn in 3/4 perspective:
#   - Top and bottom circles rendered as ellipses
#   - Right half of the bottom ellipse is dashed (hidden edge)
#   - A radius line is drawn on the top ellipse with a label


@dataclass
class CylinderDiagram:
    r: float
    h: float
    labels: bool = False
    label_r: str = ""
    label_h: str = ""
    pos: List[float] = field(default_factory=lambda: [0.0, 0.0])
    scale: float = 1.0


def parse(line: str) -> Optional[CylinderDiagram]:
    def get_num(key):
        m = re.search(rf'\b{key}:\s*(-?[\d.]+)', line)
        return float(m.group(1)) if m else None

    def get_str(key):
        m = re.search(rf'\b{key}[=:]\s*"([^"]*)"', line)
        if m:
            return m.group(1)
        m = re.search(rf'\b{key}[=:]\s*([^,)\s]+)', line)
        return m.group(1) if m else ""

    r = get_num("r")
    h = get_num("h")
    if r is None or h is None:
        return None

    pos_match = re.search(r'\bpos:\s*\(\s*(-?[\d.]+)\s*,\s*(-?[\d.]+)\s*\)', line)
    pos = [float(pos_match.group(1)), float(pos_match.group(2))] if pos_match else [0.0, 0.0]
    scale = get_num("scale") or 1.0

    labels_match = re.search(r'\blabels:\s*(true|false)', line)
    labels = (labels_match.group(1) != "false") if labels_match else False

    label_r = get_str("label_r") or (_fmt(r) if labels else "")
    label_h = get_str("label_h") or (_fmt(h) if labels else "")

    return CylinderDiagram(r=r, h=h, labels=labels, label_r=label_r, label_h=label_h,
                           pos=pos, scale=scale)


def render(d: CylinderDiagram, viz_scale: float = None) -> str:
    r = d.r * d.scale
    h = d.h * d.scale
    cx0, cy0 = d.pos

    # Ellipse radii: horizontal = r, vertical = r * ELLIPSE_RATIO (perspective foreshortening)
    ELLIPSE_RATIO = 0.35
    rx = r
    ry = r * ELLIPSE_RATIO

    # Top ellipse centre; bottom ellipse centre is h lower in SVG
    top_cx, top_cy    = cx0, cy0 - h / 2
    bot_cx, bot_cy    = cx0, cy0 + h / 2

    if viz_scale is None:
        content_w = 2 * r
        content_h = h + 2 * ry
        content_span = max(content_w, content_h * (60.0 / 36.0))
        expected_vw  = content_span / 0.92
        viz_scale    = expected_vw / 60.0

    sw        = 0.192 * viz_scale
    font_size = 2.0   * viz_scale
    out = []

    # ── Bottom ellipse ────────────────────────────────────────────────────────
    # Draw the full ellipse in grey first — <ellipse> is detected by _svg_content_bbox
    # so the auto-zoom correctly accounts for bot_cy + ry and won't clip the bottom.
    # Then overlay the front (lower) arc in black.
    out.append(
        f'<ellipse cx="{bot_cx:.3f}" cy="{bot_cy:.3f}" rx="{rx:.3f}" ry="{ry:.3f}" '
        f'fill="none" stroke="#BBB" stroke-width="{sw}"/>'
    )
    # Front arc: left-point → right-point curving downward (sweep-flag=0, counter-clockwise)
    out.append(
        f'<path d="M {bot_cx - rx:.3f},{bot_cy:.3f} '
        f'A {rx:.3f},{ry:.3f} 0 0,0 {bot_cx + rx:.3f},{bot_cy:.3f}" '
        f'fill="none" stroke="black" stroke-width="{sw}" stroke-linecap="round"/>'
    )

    # ── Vertical side edges ───────────────────────────────────────────────────
    # Left edge (visible)
    out.append(
        f'<line x1="{cx0 - rx:.3f}" y1="{top_cy:.3f}" '
        f'x2="{cx0 - rx:.3f}" y2="{bot_cy:.3f}" '
        f'stroke="black" stroke-width="{sw}" stroke-linecap="round"/>'
    )
    # Right edge (visible)
    out.append(
        f'<line x1="{cx0 + rx:.3f}" y1="{top_cy:.3f}" '
        f'x2="{cx0 + rx:.3f}" y2="{bot_cy:.3f}" '
        f'stroke="black" stroke-width="{sw}" stroke-linecap="round"/>'
    )

    # ── Top ellipse (fully solid — entirely visible) ──────────────────────────
    out.append(
        f'<ellipse cx="{top_cx:.3f}" cy="{top_cy:.3f}" rx="{rx:.3f}" ry="{ry:.3f}" '
        f'fill="none" stroke="black" stroke-width="{sw}"/>'
    )

    # Labels suppressed in pass 1 (viz_scale == 1.0) to avoid inflating the bbox
    if viz_scale != 1.0:
        # Radius line on top ellipse: centre → right edge, with label above
        if d.label_r:
            out.append(
                f'<line x1="{top_cx:.3f}" y1="{top_cy:.3f}" '
                f'x2="{top_cx + rx:.3f}" y2="{top_cy:.3f}" '
                f'stroke="black" stroke-width="{sw}" stroke-linecap="round"/>'
            )
            out.append(_text(
                top_cx + rx / 2,
                top_cy - font_size * 0.9,
                d.label_r, font_size,
            ))

        # Height label: midpoint of right edge, offset right
        if d.label_h:
            out.append(_text(
                cx0 + rx + font_size * 1.2,
                cy0,
                d.label_h, font_size,
            ))

    return "\n".join(p for p in out if p)


# ── Helpers ───────────────────────────────────────────────────────────────────

def _text(x, y, text, font_size):
    return (
        f'<text x="{x:.3f}" y="{y:.3f}" font-size="{font_size}" '
        f'font-family="system-ui, -apple-system, sans-serif" '
        f'text-anchor="middle" dominant-baseline="middle">{text}</text>'
    )


def _fmt(n: float) -> str:
    return str(int(n)) if n == int(n) else f"{n:g}"
