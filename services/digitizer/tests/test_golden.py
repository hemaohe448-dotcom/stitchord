"""Golden corpus (self-referential regression): document -> SVG -> plan/DST.

These cases are not compared to Inkscape output yet; they protect the
document/compiler/worker contract from regressions and are run under the
Python 3.11 worker environment.
"""

from __future__ import annotations

import pytest

from app import inkstitch_adapter
from app.compiler import (
    CompileDocument,
    CompileLayer,
    CompileObject,
    CompileStitch,
    compile_svg,
)
from app.models import ThreadColor

pytestmark = pytest.mark.skipif(
    not inkstitch_adapter.available(),
    reason="Ink/Stitch runtime not available in this interpreter",
)


def _obj(
    obj_id: str,
    path: str,
    color: str = "#c0392b",
    stitch: CompileStitch | None = None,
    translate: tuple[float, float] | None = None,
) -> CompileObject:
    return CompileObject(
        id=obj_id,
        path_d=path,
        color=ThreadColor(hex=color),
        stitch=stitch or CompileStitch(type="fill"),
        translate_mm=translate,
    )


def _doc(
    objects: list[CompileObject],
    fabric: str | None = "woven",
    width: float = 100,
    height: float = 100,
) -> CompileDocument:
    return CompileDocument(
        width_mm=width,
        height_mm=height,
        fabric=fabric,
        layers=[CompileLayer(id="layer-1", objects=objects)],
    )


RECT = "M 10,10 L 50,10 L 50,40 L 10,40 Z"
DIAMOND = "M 50,10 L 70,30 L 50,50 L 30,30 Z"
LINE = "M 10,50 L 50,50 L 50,80"
RAILS = "M 10,10 L 10,50 M 30,10 L 30,50"

CASES = [
    pytest.param(_doc([_obj("o1", RECT)]), id="fill-woven"),
    pytest.param(_doc([_obj("o1", RECT)], fabric="knit"), id="fill-knit"),
    pytest.param(_doc([_obj("o1", RECT)], fabric="denim"), id="fill-denim"),
    pytest.param(
        _doc([_obj("o1", RECT, "#c0392b"), _obj("o2", DIAMOND, "#2980b9")]),
        id="fill-two-colors",
    ),
    pytest.param(
        _doc([_obj("o1", LINE, "#2e7d32", CompileStitch(type="running"))]),
        id="running",
    ),
    pytest.param(
        _doc([_obj("o1", RAILS, "#c0392b", CompileStitch(type="satin"))]),
        id="satin",
    ),
    pytest.param(
        _doc([_obj("o1", DIAMOND, stitch=CompileStitch(type="fill", angle_deg=45))]),
        id="fill-angle-45",
    ),
    pytest.param(
        _doc([_obj("o1", RECT, stitch=CompileStitch(type="fill", underlay=False))]),
        id="fill-underlay-off",
    ),
    pytest.param(
        _doc([_obj("o1", RECT, stitch=CompileStitch(type="fill", row_spacing_mm=0.6))]),
        id="fill-row-0.6",
    ),
    pytest.param(
        _doc([_obj("o1", RECT, translate=(20, 10))]),
        id="fill-translated",
    ),
    pytest.param(
        _doc(
            [
                _obj("o1", "M 10,10 L 30,10 L 30,30 L 10,30 Z", "#c0392b"),
                _obj("o2", "M 40,10 L 60,10 L 60,30 L 40,30 Z", "#2980b9"),
                _obj("o3", "M 70,10 L 90,10 L 90,30 L 70,30 Z", "#2e7d32"),
            ]
        ),
        id="three-objects",
    ),
    pytest.param(
        _doc([_obj("o1", "M 20,20 L 25,20 L 25,25 L 20,25 Z")], fabric=None),
        id="small-rect-no-fabric",
    ),
]


@pytest.mark.parametrize("document", CASES)
def test_golden_case(document: CompileDocument, tmp_path):
    svg = compile_svg(document)
    svg_path = tmp_path / "design.svg"
    svg_path.write_text(svg, encoding="utf-8")

    result = inkstitch_adapter.digitize_svg(svg_path, tmp_path / "design.dst")
    plan = result.plan
    assert plan["colorBlocks"], "no color blocks"
    assert plan["stats"]["stitchCount"] > 0
    assert len(result.dst) > 100
    assert plan["schemaVersion"] == "1.0"


def test_translated_object_shifts_bounds(tmp_path):
    document = _doc([_obj("o1", RECT, translate=(20, 5))], fabric=None)
    svg_path = tmp_path / "design.svg"
    svg_path.write_text(compile_svg(document), encoding="utf-8")
    plan = inkstitch_adapter.digitize_svg(svg_path, tmp_path / "design.dst").plan
    assert plan["bounds"]["minX"] == pytest.approx(30, abs=0.3)
    assert plan["bounds"]["minY"] == pytest.approx(15, abs=0.3)


def test_golden_output_is_deterministic(tmp_path):
    document = _doc([_obj("o1", RECT), _obj("o2", DIAMOND, "#2980b9")])
    svg_path = tmp_path / "design.svg"
    svg_path.write_text(compile_svg(document), encoding="utf-8")

    first = inkstitch_adapter.digitize_svg(svg_path, tmp_path / "a.dst")
    second = inkstitch_adapter.digitize_svg(svg_path, tmp_path / "b.dst")
    assert first.dst == second.dst
    assert first.sha256 == second.sha256
