"""Tests for venn_diagram.py — excluded from the diagram auto-loader."""
import pytest
from .venn_diagram import parse, render, viewbox, VennDiagramData


def _make(only_A="12", both="5", only_B="8", neither="3", **kw):
    return VennDiagramData(only_A=only_A, both=both, only_B=only_B, neither=neither, **kw)


# ── parse() ───────────────────────────────────────────────────────────────────

def test_parse_basic():
    line = 'VennDiagram(label_A: "Sport", label_B: "Music", only_A: 12, both: 5, only_B: 8, neither: 3)'
    d = parse(line)
    assert d is not None
    assert d.label_A == "Sport"
    assert d.label_B == "Music"
    assert d.only_A == "12"
    assert d.both == "5"
    assert d.only_B == "8"
    assert d.neither == "3"


def test_parse_returns_none_for_other_diagrams():
    assert parse("TreeDiagram(branches: [])") is None
    assert parse("DataTable(headers: [A, B], rows: [(1, 2)])") is None


def test_parse_highlight_single():
    line = 'VennDiagram(only_A: 10, both: 4, only_B: 6, neither: 2, highlight: "both")'
    d = parse(line)
    assert d.highlight == ["both"]


def test_parse_highlight_list():
    line = 'VennDiagram(only_A: 10, both: 4, only_B: 6, neither: 2, highlight: ["only_A", "both", "only_B"])'
    d = parse(line)
    assert d.highlight == ["only_a", "both", "only_b"]


def test_parse_highlight_empty():
    line = 'VennDiagram(only_A: 5, both: 3, only_B: 7, neither: 1)'
    d = parse(line)
    assert d.highlight == []


def test_parse_show_labels():
    line = 'VennDiagram(only_A: 5, both: 3, only_B: 7, neither: 1, show_labels: true)'
    d = parse(line)
    assert d.show_labels is True


def test_parse_total_and_label_box():
    line = 'VennDiagram(only_A: 5, both: 3, only_B: 7, neither: 1, total: 16, label_box: "Students")'
    d = parse(line)
    assert d.total == "16"
    assert d.label_box == "Students"


def test_parse_pos():
    line = 'VennDiagram(only_A: 5, both: 3, only_B: 7, neither: 1, pos: (-10, 5))'
    d = parse(line)
    assert d.pos == (-10.0, 5.0)


# ── viewbox() ─────────────────────────────────────────────────────────────────

def test_viewbox_shape():
    d = _make()
    vb = viewbox(d)
    assert len(vb) == 4
    x, y, w, h = vb
    assert w > 0 and h > 0
    # centre should be near 0
    assert abs(x + w / 2) < 0.1
    assert abs(y + h / 2) < 0.1


# ── render() ──────────────────────────────────────────────────────────────────

def test_render_contains_circles():
    svg = render(_make())
    assert svg.count("<circle") >= 2


def test_render_counts_appear():
    svg = render(_make(only_A="12", both="5", only_B="8", neither="3"))
    assert "12" in svg
    assert "5" in svg
    assert "8" in svg
    assert "3" in svg


def test_render_highlight_both():
    d = _make(highlight=["both"])
    svg = render(d)
    assert "#E6F1FB" in svg   # highlight fill colour
    assert "#185FA5" in svg   # highlight stroke colour


def test_render_highlight_union():
    d = _make(highlight=["only_A", "both", "only_B"])
    svg = render(d)
    assert "#E6F1FB" in svg
    # crescent A + lens + crescent B = 3 highlight fill elements
    assert svg.count('fill="#E6F1FB"') >= 3


def test_render_show_labels():
    d = _make(label_A="Cats", label_B="Dogs", show_labels=True)
    svg = render(d)
    assert "Cats only" in svg
    assert "Dogs only" in svg
    assert "Both" in svg
    assert "Neither" in svg
