import re
import math
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

DIAGRAM_TYPE = "TreeDiagram"
SUPPORTS_VIZ_SCALE = True

# Syntax:
#   TreeDiagram(
#     stages: ["Draw 1", "Draw 2"],
#     branches: [["Red", "Red"], ["Red", "Green"], ["Green", "Red"], ["Green", "Green"]],
#     probs: [["2/7", "1/6"], ["2/7", "5/6"], ["5/7", "2/6"], ["5/7", "5/6"]],
#     end_labels: ["2/42", "10/42", "10/42", "25/42"],
#     highlight: [3],
#     pos: (0, 0)
#   )
#
# branches  — required. Each entry is one root-to-leaf path; shared prefixes
#             collapse into shared nodes automatically.
# stages    — optional column header labels, one per depth level.
# probs     — optional; same shape as branches. Probability label per branch.
# end_labels — optional; one label per path (right of leaf).
# highlight — optional; 0-based path indices to emphasise in accent blue.


# ── Colours ───────────────────────────────────────────────────────────────────
_C_LINE    = "#374151"
_C_ACCENT  = "#2563eb"
_C_MUTED   = "#9ca3af"
_C_NODE    = "#374151"
_C_NODE_HL = "#2563eb"
_C_TEXT    = "#374151"
_C_TEXT_MU = "#9ca3af"
_FONT      = "system-ui, -apple-system, sans-serif"


@dataclass
class TreeDiagramData:
    stages:     List[str]       = field(default_factory=list)
    branches:   List[List[str]] = field(default_factory=list)
    probs:      List[List[str]] = field(default_factory=list)
    end_labels: List[str]       = field(default_factory=list)
    highlight:  List[int]       = field(default_factory=list)
    pos:        Tuple[float, float] = (0.0, 0.0)


# ── Parsing helpers ────────────────────────────────────────────────────────────

def _extract_balanced(text: str, key: str) -> Optional[str]:
    """Return the content between the opening [ and its matching ] for `key`."""
    m = re.search(rf'\b{re.escape(key)}:\s*\[', text)
    if not m:
        return None
    start = m.end()
    depth = 1
    i = start
    while i < len(text) and depth > 0:
        c = text[i]
        if c == '[':
            depth += 1
        elif c == ']':
            depth -= 1
        i += 1
    return text[start:i - 1] if depth == 0 else None


def _parse_string_list(content: str) -> List[str]:
    return [m.group(1) for m in re.finditer(r'"([^"]*)"', content)]


def _parse_list_of_lists(content: str) -> List[List[str]]:
    result: List[List[str]] = []
    depth = 0
    start = None
    for i, c in enumerate(content):
        if c == '[':
            if depth == 0:
                start = i + 1
            depth += 1
        elif c == ']':
            depth -= 1
            if depth == 0 and start is not None:
                result.append(_parse_string_list(content[start:i]))
    return result


def _parse_int_list(content: str) -> List[int]:
    return [int(m.group(0)) for m in re.finditer(r'\d+', content)]


def _to_svg_text(s: str) -> str:
    """Convert \\frac{a}{b} to a/b for plain-text SVG rendering."""
    m = re.fullmatch(r'\\frac\{(\d+)\}\{(\d+)\}', s.strip())
    return f"{m.group(1)}/{m.group(2)}" if m else s


def _esc(s: str) -> str:
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def parse(line: str) -> Optional[TreeDiagramData]:
    if not line.startswith("TreeDiagram"):
        return None

    branches_raw = _extract_balanced(line, "branches")
    branches = _parse_list_of_lists(branches_raw) if branches_raw else []

    stages_raw = _extract_balanced(line, "stages")
    stages = _parse_string_list(stages_raw) if stages_raw else []

    probs_raw = _extract_balanced(line, "probs")
    probs = _parse_list_of_lists(probs_raw) if probs_raw else []

    end_raw = _extract_balanced(line, "end_labels")
    end_labels = _parse_string_list(end_raw) if end_raw else []

    hl_raw = _extract_balanced(line, "highlight")
    highlight = _parse_int_list(hl_raw) if hl_raw else []

    pos_m = re.search(r'\bpos:\s*\(\s*(-?[\d.]+)\s*,\s*(-?[\d.]+)\s*\)', line)
    pos = (float(pos_m.group(1)), float(pos_m.group(2))) if pos_m else (0.0, 0.0)

    return TreeDiagramData(
        stages=stages,
        branches=branches,
        probs=probs,
        end_labels=end_labels,
        highlight=highlight,
        pos=pos,
    )


# ── Tree node ─────────────────────────────────────────────────────────────────

class _Node:
    __slots__ = ('stage', 'label', 'children', 'x', 'y', 'path_indices')

    def __init__(self, stage: int, label: str) -> None:
        self.stage = stage
        self.label = label
        self.children: Dict[str, '_Node'] = {}
        self.x = 0.0
        self.y = 0.0
        self.path_indices: List[int] = []


def _build_tree(branches: List[List[str]]) -> _Node:
    root = _Node(-1, "")
    for path_idx, path in enumerate(branches):
        root.path_indices.append(path_idx)
        node = root
        for label in path:
            if label not in node.children:
                node.children[label] = _Node(node.stage + 1, label)
            node = node.children[label]
            node.path_indices.append(path_idx)
    return root


# ── Render ────────────────────────────────────────────────────────────────────

def render(d: TreeDiagramData, viz_scale: float = None) -> str:
    ox, oy = d.pos

    if not d.branches:
        fw, fh = 22.0, 7.0
        return (
            f'<rect x="{ox - fw/2:.2f}" y="{oy - fh/2:.2f}" '
            f'width="{fw:.2f}" height="{fh:.2f}" '
            f'fill="#f9fafb" stroke="#9ca3af" stroke-width="0.3" rx="1"/>'
            f'<text x="{ox:.2f}" y="{oy:.2f}" font-size="2.0" '
            f'font-family="{_FONT}" fill="#9ca3af" '
            f'text-anchor="middle" dominant-baseline="middle">'
            f'No branches defined</text>'
        )

    if viz_scale is None:
        viz_scale = 1.0

    n_stages = max(len(p) for p in d.branches)
    highlight_set = set(d.highlight)
    has_hl = bool(highlight_set)

    # ── Build tree ────────────────────────────────────────────────────────────
    root = _build_tree(d.branches)

    # ── Assign x positions ────────────────────────────────────────────────────
    x_root   = ox - 22.0
    x_leaves = ox + 18.0
    x_step   = (x_leaves - x_root) / n_stages if n_stages else 1.0
    root.x   = x_root

    def _assign_x(node: _Node) -> None:
        for child in node.children.values():
            child.x = x_root + (child.stage + 1) * x_step
            _assign_x(child)

    _assign_x(root)

    # ── Collect leaves in DFS order ───────────────────────────────────────────
    leaves: List[_Node] = []

    def _collect_leaves(node: _Node) -> None:
        if not node.children:
            leaves.append(node)
        else:
            for child in node.children.values():
                _collect_leaves(child)

    _collect_leaves(root)
    n_leaves = len(leaves)

    # ── Assign y positions ────────────────────────────────────────────────────
    y_span = min(28.0, n_leaves * 5.5)
    if n_leaves > 1:
        y_step_v = y_span / (n_leaves - 1)
        y_top    = oy - y_span / 2
        for i, lf in enumerate(leaves):
            lf.y = y_top + i * y_step_v
    else:
        leaves[0].y = oy
        y_top = oy

    def _assign_y_int(node: _Node) -> None:
        if not node.children:
            return
        for child in node.children.values():
            _assign_y_int(child)
        node.y = sum(c.y for c in node.children.values()) / len(node.children)

    _assign_y_int(root)

    # ── Build edge table ──────────────────────────────────────────────────────
    # edges: dict keyed by (id(parent), id(child)) → {'parent', 'child', 'prob', 'paths'}
    edges: Dict[tuple, dict] = {}

    for path_idx, path in enumerate(d.branches):
        node = root
        for stage_idx, label in enumerate(path):
            child = node.children[label]
            ek = (id(node), id(child))
            prob_str = ""
            if (d.probs
                    and path_idx < len(d.probs)
                    and stage_idx < len(d.probs[path_idx])):
                prob_str = _to_svg_text(d.probs[path_idx][stage_idx])
            if ek not in edges:
                edges[ek] = {
                    'parent': node,
                    'child':  child,
                    'prob':   prob_str,
                    'paths':  {path_idx},
                }
            else:
                edges[ek]['paths'].add(path_idx)
            node = child

    edge_list = list(edges.values())

    # ── Sizing ────────────────────────────────────────────────────────────────
    sw         = 0.18  * viz_scale
    sw_hl      = 0.38  * viz_scale
    node_r     = 0.50  * viz_scale
    fs         = 2.00  * viz_scale   # main font
    fs_sm      = 1.75  * viz_scale   # branch / end labels
    prob_off   = 1.60  * viz_scale   # perpendicular offset for prob labels
    node_label_dy = 1.70 * viz_scale  # label below node dot

    out: List[str] = []

    # ── Stage headers ─────────────────────────────────────────────────────────
    if d.stages:
        header_y = (oy - y_span / 2) - 4.0 * viz_scale
        for i, s_label in enumerate(d.stages):
            sx = x_root + (i + 1) * x_step
            out.append(
                f'<text x="{sx:.3f}" y="{header_y:.3f}" '
                f'font-size="{fs:.2f}" font-family="{_FONT}" '
                f'fill="{_C_TEXT}" font-weight="bold" '
                f'text-anchor="middle" dominant-baseline="middle">'
                f'{_esc(s_label)}</text>'
            )

    # ── Branch lines ──────────────────────────────────────────────────────────
    for e in edge_list:
        p, c = e['parent'], e['child']
        is_hl = bool(highlight_set & e['paths'])

        if has_hl:
            color    = _C_ACCENT if is_hl else _C_MUTED
            stroke_w = sw_hl if is_hl else sw
        else:
            color    = _C_LINE
            stroke_w = sw

        out.append(
            f'<line x1="{p.x:.3f}" y1="{p.y:.3f}" '
            f'x2="{c.x:.3f}" y2="{c.y:.3f}" '
            f'stroke="{color}" stroke-width="{stroke_w:.3f}" '
            f'stroke-linecap="round"/>'
        )

        # Prob label at midpoint, offset above the line
        if e['prob']:
            mx = (p.x + c.x) / 2
            my = (p.y + c.y) / 2
            dx = c.x - p.x
            dy = c.y - p.y
            length = math.hypot(dx, dy)
            if length > 0.01:
                nx = -dy / length
                ny =  dx / length
                if ny > 0:        # ensure normal points upward in SVG (negative y)
                    nx, ny = -nx, -ny
                lx = mx + nx * prob_off
                ly = my + ny * prob_off
            else:
                lx, ly = mx, my - prob_off

            tc = _C_ACCENT if (has_hl and is_hl) else (_C_TEXT_MU if has_hl else _C_TEXT)
            out.append(
                f'<text x="{lx:.3f}" y="{ly:.3f}" '
                f'font-size="{fs_sm:.2f}" font-family="{_FONT}" '
                f'fill="{tc}" text-anchor="middle" dominant-baseline="auto">'
                f'{_esc(e["prob"])}</text>'
            )

    # ── Nodes and outcome labels ───────────────────────────────────────────────
    def _draw_node(node: _Node) -> None:
        if node.stage == -1:
            out.append(
                f'<circle cx="{node.x:.3f}" cy="{node.y:.3f}" '
                f'r="{node_r:.3f}" fill="{_C_NODE}" stroke="none"/>'
            )
            for child in node.children.values():
                _draw_node(child)
            return

        is_hl = has_hl and bool(highlight_set & set(node.path_indices))
        fill   = _C_NODE_HL if is_hl else (_C_MUTED if has_hl else _C_NODE)
        tc     = _C_ACCENT  if is_hl else (_C_TEXT_MU if has_hl else _C_TEXT)

        out.append(
            f'<circle cx="{node.x:.3f}" cy="{node.y:.3f}" '
            f'r="{node_r:.3f}" fill="{fill}" stroke="none"/>'
        )

        # Outcome label below the dot
        lx = node.x
        ly = node.y + node_label_dy
        out.append(
            f'<text x="{lx:.3f}" y="{ly:.3f}" '
            f'font-size="{fs_sm:.2f}" font-family="{_FONT}" '
            f'fill="{tc}" font-weight="bold" text-anchor="middle" dominant-baseline="hanging">'
            f'{_esc(node.label)}</text>'
        )

        for child in node.children.values():
            _draw_node(child)

    _draw_node(root)

    # ── End labels ────────────────────────────────────────────────────────────
    if d.end_labels:
        gap = 2.0 * viz_scale
        for i, lf in enumerate(leaves):
            if i >= len(d.end_labels):
                break
            label = _to_svg_text(d.end_labels[i])
            is_hl = has_hl and (i in highlight_set)
            tc = _C_ACCENT if is_hl else (_C_TEXT_MU if has_hl else _C_TEXT)
            ex = lf.x + gap
            out.append(
                f'<text x="{ex:.3f}" y="{lf.y:.3f}" '
                f'font-size="{fs_sm:.2f}" font-family="{_FONT}" '
                f'fill="{tc}" text-anchor="start" dominant-baseline="middle">'
                f'{_esc(label)}</text>'
            )

    return "\n".join(s for s in out if s)
