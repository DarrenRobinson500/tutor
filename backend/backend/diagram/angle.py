import re
import math
from dataclasses import dataclass, field
from typing import List, Optional, Dict

DIAGRAM_TYPE = "Angle"
SUPPORTS_VIZ_SCALE = True

# ── New syntax ────────────────────────────────────────────────────────────────
# Angle(A: 30, B: 90, C: 20, size: 180, label_A: "A", arcs_A: 2)
#
#   A / B / C …   — named angle segments in degrees (uppercase single letter)
#   size          — total extent: 90, 180, or 360
#                   if omitted, defaults to the sum of the named angles (old-style)
#   label_X       — override display label for angle X  (default = "30°" etc.)
#                   set to "" to hide the label
#   arcs_X / arc_X — number of concentric arcs to draw for angle X (default 1)
#   labels        — set to false to hide all labels globally
#
# Legacy syntax still supported: Angle(deg: 65)
# ─────────────────────────────────────────────────────────────────────────────

_RAY_LEN   = 12.0   # ray length at viz_scale = 1.0
_SW        = 0.18   # stroke-width for rays
_ARC_SW    = 0.13   # stroke-width for arcs
_ARC_R0    = 2.8    # innermost arc radius
_ARC_DR    = 1.05   # radial step between multiple arcs for the same angle
_FONT_SIZE = 2.8    # label font size
_LABEL_GAP = 2.2    # extra radial gap between outermost arc and label


@dataclass
class AngleDiagram:
    names:       List[str]        # e.g. ["A", "B", "C"]
    angles:      List[float]      # degrees for each segment
    size:        Optional[float]  # total extent (90 / 180 / 360) or None = auto
    labels:      Dict[str, str]   # name → label text override
    arcs:        Dict[str, int]   # name → arc count
    show_labels: bool = True      # False = suppress all labels globally


def parse(line: str) -> Optional[AngleDiagram]:
    # ── Size ──────────────────────────────────────────────────────────────────
    size_match = re.search(r'\bsize:\s*(90|180|360)\b', line)
    size = float(size_match.group(1)) if size_match else None

    # ── Named angles: single uppercase letter followed by colon + number ──────
    # \b ensures we don't match the A inside label_A or arcs_A (preceded by _)
    angle_matches = re.findall(r'(?<![_\w])([A-Z]):\s*([\d.]+)', line)
    names  = [m[0] for m in angle_matches]
    angles = [float(m[1]) for m in angle_matches]

    # ── Labels: label_A: "text" or label_A: 'text' ────────────────────────────
    labels: Dict[str, str] = {}
    for m in re.finditer(r'\blabel_([A-Z]):\s*["\']([^"\']*)["\']', line):
        labels[m.group(1)] = m.group(2)

    # ── Arc counts: arcs_A: 2  or  arc_A: 2 ──────────────────────────────────
    arcs: Dict[str, int] = {}
    for m in re.finditer(r'\barcs?_([A-Z]):\s*(\d+)', line):
        arcs[m.group(1)] = int(m.group(2))

    # ── Global label toggle: labels: false ────────────────────────────────────
    labels_match = re.search(r'\blabels:\s*(true|false)', line)
    show_labels = (labels_match.group(1) != "false") if labels_match else True

    # ── Infer implied angles from labels/arcs that have no explicit angle ──────
    # e.g. Angle(A: 125, B: 130, label_C: "x", arc_C: 3, size: 360)
    # → C is implied as 360 - 125 - 130 = 105°
    implied = sorted(k for k in (set(labels) | set(arcs)) if k not in names)
    if implied and size is not None:
        remaining = size - sum(angles)
        if remaining > 0:
            if len(implied) == 1:
                names.append(implied[0])
                angles.append(remaining)
            else:
                # Multiple implied angles: split remaining equally
                per = remaining / len(implied)
                for k in implied:
                    names.append(k)
                    angles.append(per)

    # ── Legacy: Angle(deg: 65) ────────────────────────────────────────────────
    if not names:
        deg_match = re.search(r'\bdeg:\s*([\d.]+)', line)
        if not deg_match:
            return None
        deg = float(deg_match.group(1))
        if deg <= 0 or deg >= 360:
            return None
        names  = ['A']
        angles = [deg]

    return AngleDiagram(names=names, angles=angles, size=size,
                        labels=labels, arcs=arcs, show_labels=show_labels)


def _ray(cx, cy, theta_deg, length, sw):
    rad = math.radians(theta_deg)
    rx  = cx + length * math.cos(rad)
    ry  = cy - length * math.sin(rad)   # SVG y is flipped
    return (f'<line x1="{cx:.2f}" y1="{cy:.2f}" '
            f'x2="{rx:.2f}" y2="{ry:.2f}" '
            f'stroke="black" stroke-width="{sw}" stroke-linecap="round"/>')


def _arc(cx, cy, r, start_deg, end_deg, sw):
    span = end_deg - start_deg
    # 360° full-circle — SVG arc command can't draw start=end, use circle instead
    if abs(span - 360.0) < 1e-6:
        return f'<circle cx="{cx:.2f}" cy="{cy:.2f}" r="{r:.2f}" fill="none" stroke="black" stroke-width="{sw}"/>'
    # 90° angles get a square corner marker instead of a curved arc
    if abs(span - 90.0) < 1e-6:
        s_rad = math.radians(start_deg)
        e_rad = math.radians(end_deg)
        # Unit vectors along each ray
        ux0, uy0 =  math.cos(s_rad), -math.sin(s_rad)
        ux1, uy1 =  math.cos(e_rad), -math.sin(e_rad)
        # Three corners of the square: along ray 0, diagonal, along ray 1
        p0x = cx + r * ux0;  p0y = cy + r * uy0
        p1x = cx + r * (ux0 + ux1);  p1y = cy + r * (uy0 + uy1)
        p2x = cx + r * ux1;  p2y = cy + r * uy1
        return (f'<path d="M{p0x:.2f},{p0y:.2f} L{p1x:.2f},{p1y:.2f} L{p2x:.2f},{p2y:.2f}" '
                f'fill="none" stroke="black" stroke-width="{sw}" '
                f'stroke-linejoin="miter" stroke-linecap="butt"/>')
    large = 1 if span > 180 else 0
    s_rad = math.radians(start_deg)
    e_rad = math.radians(end_deg)
    ax0 = cx + r * math.cos(s_rad);  ay0 = cy - r * math.sin(s_rad)
    ax1 = cx + r * math.cos(e_rad);  ay1 = cy - r * math.sin(e_rad)
    return (f'<path d="M{ax0:.2f},{ay0:.2f} '
            f'A{r:.2f},{r:.2f} 0 {large},0 {ax1:.2f},{ay1:.2f}" '
            f'fill="none" stroke="black" stroke-width="{sw}"/>')


def render(d: AngleDiagram, viz_scale: float = None) -> str:
    cx, cy = 0.0, 0.0

    # ── Cumulative boundary angles (needed for viz_scale estimate too) ─────────
    cum = [0.0]
    for a in d.angles:
        cum.append(cum[-1] + a)
    total = cum[-1]

    effective_size = d.size if d.size is not None else total

    ray_angles = list(cum)
    if total < effective_size - 1e-9:
        ray_angles.append(effective_size)
    if effective_size == 360:
        ray_angles = [a for a in ray_angles if abs(a - 360) > 1e-9]

    # ── Derive viz_scale from ray extent when not supplied (pass-1 self-sizing) ─
    if viz_scale is None:
        all_x = [cx + _RAY_LEN * math.cos(math.radians(t)) for t in ray_angles] + [cx]
        all_y = [cy - _RAY_LEN * math.sin(math.radians(t)) for t in ray_angles] + [cy]
        content_w = max(all_x) - min(all_x) or 1.0
        content_h = max(all_y) - min(all_y) or 1.0
        content_span = max(content_w, content_h * (60.0 / 36.0))
        viz_scale = (content_span / 0.92) / 60.0

    ray_len   = _RAY_LEN             # geometry — fixed, not scaled
    arc_r0    = _ARC_R0              # geometry — fixed, not scaled
    arc_dr    = _ARC_DR              # geometry — fixed, not scaled
    label_gap = _LABEL_GAP           # geometry — fixed, not scaled
    sw        = _SW        * viz_scale
    arc_sw    = _ARC_SW    * viz_scale
    font_size = _FONT_SIZE * viz_scale

    parts = []

    # ── Draw boundary rays ────────────────────────────────────────────────────
    for theta in ray_angles:
        parts.append(_ray(cx, cy, theta, ray_len, sw))

    # ── For each named angle: arcs + label ────────────────────────────────────
    for i, name in enumerate(d.names):
        start_deg = cum[i]
        end_deg   = cum[i + 1]
        span      = d.angles[i]
        n_arcs    = d.arcs.get(name, 1)

        # Label text (empty = hidden)
        if not d.show_labels:
            label_text = ""
        elif name in d.labels:
            label_text = d.labels[name]
        else:
            label_text = f"{int(span)}°" if span == int(span) else f"{span}°"

        # Arcs
        for k in range(n_arcs):
            r = arc_r0 + k * arc_dr
            parts.append(_arc(cx, cy, r, start_deg, end_deg, arc_sw))

        # Label suppressed in pass 1 (viz_scale == 1.0) to avoid inflating the bbox
        if label_text and viz_scale != 1.0:
            bis_deg = (start_deg + end_deg) / 2
            bis_rad = math.radians(bis_deg)
            label_r = arc_r0 + n_arcs * arc_dr + label_gap
            lx = cx + label_r * math.cos(bis_rad)
            ly = cy - label_r * math.sin(bis_rad)
            parts.append(
                f'<text x="{lx:.2f}" y="{ly:.2f}" text-anchor="middle" '
                f'dominant-baseline="middle" font-size="{font_size}" '
                f'font-family="system-ui,-apple-system,sans-serif" '
                f'fill="black">{label_text}</text>'
            )

    return "\n".join(parts)
