import re
from dataclasses import dataclass, field
from typing import Optional, Tuple, List

DIAGRAM_TYPE = "NumberLine"

# Examples:
# NumberLine(min: 0, max: 10)
# NumberLine(min: 0, max: 10, arrows: [(2, 7)])
# NumberLine(min: 0, max: 10, dots: [5, 6])
# NumberLine(min: 0, max: 10, arrows: [(2, 7)], dots: [5], pos: (0, 0))

@dataclass
class NumberLineDiagram:
    type: str
    min_val: float
    max_val: float
    arrows: List[Tuple[float, float]] = field(default_factory=list)
    dots: List[float] = field(default_factory=list)
    pos: Tuple[float, float] = (0.0, 0.0)


ARROW_REGEX = re.compile(r"\(\s*(-?\d+(?:\.\d+)?)\s*,\s*(-?\d+(?:\.\d+)?)\s*\)")
DOT_REGEX = re.compile(r"-?\d+(?:\.\d+)?")


def _extract_bracket(s: str, start: int) -> Tuple[str, int]:
    """Return the content inside [...] starting at index start, and the end index."""
    assert s[start] == "["
    depth = 0
    for i in range(start, len(s)):
        if s[i] == "[":
            depth += 1
        elif s[i] == "]":
            depth -= 1
            if depth == 0:
                return s[start + 1:i], i + 1
    return s[start + 1:], len(s)


def _extract_paren(s: str, start: int) -> Tuple[str, int]:
    """Return the content inside (...) starting at index start, and the end index."""
    assert s[start] == "("
    depth = 0
    for i in range(start, len(s)):
        if s[i] == "(":
            depth += 1
        elif s[i] == ")":
            depth -= 1
            if depth == 0:
                return s[start + 1:i], i + 1
    return s[start + 1:], len(s)


def parse(line: str) -> Optional[NumberLineDiagram]:
    # Strip "NumberLine(" prefix and trailing ")"
    line = line.strip()
    if not line.startswith("NumberLine(") or not line.endswith(")"):
        return None
    inner = line[len("NumberLine("):-1].strip()

    # Parse key: value pairs, respecting brackets/parens
    keys = {}
    i = 0
    while i < len(inner):
        # Skip whitespace and commas between entries
        while i < len(inner) and inner[i] in " \t,":
            i += 1
        if i >= len(inner):
            break
        # Read key
        colon = inner.find(":", i)
        if colon == -1:
            break
        key = inner[i:colon].strip()
        i = colon + 1
        # Skip whitespace
        while i < len(inner) and inner[i] in " \t":
            i += 1
        if i >= len(inner):
            break
        # Read value — could be [...] or (...) or a plain scalar
        if inner[i] == "[":
            val, i = _extract_bracket(inner, i)
            keys[key] = "[" + val + "]"
        elif inner[i] == "(":
            val, i = _extract_paren(inner, i)
            keys[key] = "(" + val + ")"
        else:
            # Scalar: read until next comma (not inside brackets/parens)
            j = i
            while j < len(inner) and inner[j] != ",":
                j += 1
            keys[key] = inner[i:j].strip()
            i = j

    # arrows — optional (parse early so we can infer min/max)
    arrows: List[Tuple[float, float]] = []
    if "arrows" in keys:
        for m in ARROW_REGEX.finditer(keys["arrows"]):
            arrows.append((float(m.group(1)), float(m.group(2))))

    # dots — optional (parse early so we can infer min/max)
    dots: List[float] = []
    if "dots" in keys:
        dots = [float(m.group()) for m in DOT_REGEX.finditer(keys["dots"])]

    # Collect all values to infer missing min/max
    all_vals = dots + [v for pair in arrows for v in pair]

    try:
        min_val = float(keys["min"]) if "min" in keys else (min(all_vals) - 2 if all_vals else 0)
        max_val = float(keys["max"]) if "max" in keys else (max(all_vals) + 2 if all_vals else 10)
    except ValueError:
        return None

    # pos — optional, default (0, 0)
    px, py = 0.0, 0.0
    if "pos" in keys:
        m = re.match(r"\(\s*(-?\d+(?:\.\d+)?)\s*,\s*(-?\d+(?:\.\d+)?)\s*\)", keys["pos"])
        if m:
            px, py = float(m.group(1)), float(m.group(2))

    return NumberLineDiagram(
        type="NumberLine",
        min_val=min_val,
        max_val=max_val,
        arrows=arrows,
        dots=dots,
        pos=(px, py),
    )


def render(nl: NumberLineDiagram) -> str:
    min_val = nl.min_val
    max_val = nl.max_val
    px, py = nl.pos

    # Visual scaling
    line_length = 50  # SVG units
    scale = line_length / (max_val - min_val)

    # Center the number line at pos
    x0 = px - line_length / 2
    y0 = py

    fragments = []

    # Arrowhead definition
    fragments.append(
        '<defs>'
        '<marker id="arrowhead" markerWidth="3" markerHeight="3" refX="2.5" refY="1.5"'
        ' orient="auto" markerUnits="strokeWidth">'
        '<path d="M0,0 L0,3 L3,1.5 z" fill="blue" />'
        '</marker>'
        '</defs>'
    )

    # Base line
    fragments.append(
        f'<line x1="{x0}" y1="{y0}" x2="{x0 + line_length}" y2="{y0}" stroke="black" stroke-width="0.5" />'
    )

    # Determine label step
    count = int(max_val) - int(min_val) + 1
    if count <= 11:
        step = 1
    elif count <= 21:
        step = 2
    else:
        step = 5

    # Tick marks + labels
    for v in range(int(min_val), int(max_val) + 1):
        xv = x0 + (v - min_val) * scale
        fragments.append(
            f'<line x1="{xv}" y1="{y0}" x2="{xv}" y2="{y0 - 2}" stroke="black" stroke-width="0.25" />'
        )
        if (v - min_val) % step == 0:
            fragments.append(
                f'<text x="{xv}" y="{y0 + 6}" font-size="4" text-anchor="middle">{v}</text>'
            )

    # Arrows
    num_arrows = len(nl.arrows)
    for i, (start, end) in enumerate(nl.arrows):
        offset = 3 * (num_arrows - i)
        arrow_y = y0 - offset
        sx = x0 + (start - min_val) * scale
        ex = x0 + (end - min_val) * scale
        fragments.append(
            f'<line x1="{sx}" y1="{arrow_y}" x2="{ex}" y2="{arrow_y}" '
            f'stroke="blue" stroke-width="0.5" marker-end="url(#arrowhead)" />'
        )

    # Dots
    for v in nl.dots:
        xv = x0 + (v - min_val) * scale
        fragments.append(
            f'<circle cx="{xv}" cy="{y0}" r="1.5" fill="blue" />'
        )

    return "\n".join(fragments)
