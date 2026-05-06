"""Tests for the TreeDiagram diagram component."""
import pytest
from .tree_diagram import parse, render, TreeDiagramData, _C_ACCENT, _C_MUTED


# ── helpers ───────────────────────────────────────────────────────────────────

def _svg(code: str, viz_scale: float = 2.0) -> str:
    d = parse(code)
    assert d is not None, "parse() returned None"
    return render(d, viz_scale=viz_scale)


# ── Test 1: two-stage coin flip, no probs, no end labels ──────────────────────

def test_coin_flip_basic():
    code = (
        'TreeDiagram('
        'stages: ["Flip 1", "Flip 2"], '
        'branches: [["H", "H"], ["H", "T"], ["T", "H"], ["T", "T"]]'
        ')'
    )
    d = parse(code)
    assert d is not None
    assert d.stages == ["Flip 1", "Flip 2"]
    assert len(d.branches) == 4
    assert d.probs == []
    assert d.end_labels == []
    assert d.highlight == []

    svg = render(d, viz_scale=2.0)
    assert "<line" in svg          # branch lines drawn
    assert "<circle" in svg        # node dots drawn
    assert "Flip 1" in svg         # stage headers
    assert "Flip 2" in svg
    assert ">H<" in svg            # outcome labels
    assert ">T<" in svg
    # No accent colour when no highlight
    assert _C_ACCENT not in svg
    assert _C_MUTED not in svg


# ── Test 2: non-uniform tree (3 × 2), probs and end labels ────────────────────

def test_non_uniform_with_probs_and_end_labels():
    code = (
        'TreeDiagram('
        'branches: [["A", "X"], ["A", "Y"], ["B", "X"], ["B", "Y"], ["C", "X"], ["C", "Y"]], '
        'probs: [["1/3", "1/2"], ["1/3", "1/2"], ["1/3", "1/2"], ["1/3", "1/2"], ["1/3", "1/2"], ["1/3", "1/2"]], '
        'end_labels: ["1/6", "1/6", "1/6", "1/6", "1/6", "1/6"]'
        ')'
    )
    d = parse(code)
    assert d is not None
    assert len(d.branches) == 6
    assert len(d.probs) == 6
    assert all(len(p) == 2 for p in d.probs)
    assert len(d.end_labels) == 6

    svg = render(d, viz_scale=2.0)
    assert "1/3" in svg            # prob label
    assert "1/2" in svg
    assert "1/6" in svg            # end label
    # 3 unique stage-1 nodes: A, B, C; 2 unique stage-2 nodes per parent: X, Y
    assert ">A<" in svg
    assert ">B<" in svg
    assert ">C<" in svg
    assert ">X<" in svg
    assert ">Y<" in svg


# ── Test 3: marble bag, highlight Green → Green (path index 3) ────────────────

def test_marble_bag_highlight():
    code = (
        'TreeDiagram('
        'stages: ["Draw 1", "Draw 2"], '
        'branches: [["Red", "Red"], ["Red", "Green"], ["Green", "Red"], ["Green", "Green"]], '
        'probs: [["2/7", "1/6"], ["2/7", "5/6"], ["5/7", "2/6"], ["5/7", "5/6"]], '
        'end_labels: ["2/42", "10/42", "10/42", "25/42"], '
        'highlight: [3]'
        ')'
    )
    d = parse(code)
    assert d is not None
    assert d.highlight == [3]

    svg = render(d, viz_scale=2.0)

    # Highlighted path uses accent colour
    assert _C_ACCENT in svg
    # Non-highlighted paths use muted colour
    assert _C_MUTED in svg

    # Stage headers present
    assert "Draw 1" in svg
    assert "Draw 2" in svg

    # Prob labels
    assert "2/7" in svg
    assert "5/7" in svg
    assert "5/6" in svg

    # End labels
    assert "25/42" in svg
    assert "2/42" in svg


# ── Test 4: three-stage tree stays within canvas ──────────────────────────────

def test_three_stage_no_overflow():
    # 2 branches per stage → 8 leaves
    branches = [
        ["A", "C", "E"], ["A", "C", "F"],
        ["A", "D", "E"], ["A", "D", "F"],
        ["B", "C", "E"], ["B", "C", "F"],
        ["B", "D", "E"], ["B", "D", "F"],
    ]
    branches_str = ", ".join(f'["{a}", "{b}", "{c}"]' for a, b, c in branches)
    code = f'TreeDiagram(branches: [{branches_str}])'
    d = parse(code)
    assert d is not None
    assert len(d.branches) == 8

    svg = render(d, viz_scale=1.0)  # pass-1 scale
    assert "<line" in svg
    assert "<circle" in svg

    # Extract all x1/x2/cx from the SVG and verify nothing is wildly out of bounds.
    import re
    coords_x = [float(m) for m in re.findall(r'(?:x1|x2|cx)="(-?[\d.]+)"', svg)]
    assert coords_x, "No x coordinates found"
    assert min(coords_x) >= -35, f"x underflow: {min(coords_x)}"
    assert max(coords_x) <= 35,  f"x overflow: {max(coords_x)}"


# ── Test 5: {{ }} substitution — values resolved before parsing ───────────────

def test_substitution_in_probs():
    # After template substitution the {{ }} are replaced with plain values.
    # Simulate pre-substituted diagram code:
    code = (
        'TreeDiagram('
        'branches: [["Green", "Green"], ["Green", "Other"], ["Other", "Green"], ["Other", "Other"]], '
        'probs: [["5/7", "4/6"], ["5/7", "2/6"], ["2/7", "5/6"], ["2/7", "1/6"]], '
        'end_labels: ["20/42", "10/42", "10/42", "2/42"]'
        ')'
    )
    d = parse(code)
    assert d is not None
    assert d.probs[0][0] == "5/7"
    assert d.probs[0][1] == "4/6"
    assert d.end_labels[0] == "20/42"

    svg = render(d, viz_scale=2.0)
    assert "5/7" in svg
    assert "4/6" in svg
    assert "20/42" in svg


# ── Test 6: missing branches renders placeholder ───────────────────────────────

def test_no_branches_placeholder():
    d = parse('TreeDiagram()')
    assert d is not None
    svg = render(d, viz_scale=2.0)
    assert "No branches defined" in svg


# ── Test 7: LaTeX fraction strings in probs ────────────────────────────────────

def test_latex_frac_in_probs():
    code = (
        'TreeDiagram('
        r'branches: [["H", "H"], ["H", "T"]], '
        r'probs: [["\frac{1}{2}", "\frac{1}{2}"], ["\frac{1}{2}", "\frac{1}{2}"]]'
        ')'
    )
    d = parse(code)
    assert d is not None
    svg = render(d, viz_scale=2.0)
    # \frac{1}{2} should render as 1/2 in plain SVG text
    assert "1/2" in svg
    assert r"\frac" not in svg
