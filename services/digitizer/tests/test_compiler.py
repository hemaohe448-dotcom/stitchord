from __future__ import annotations

import xml.etree.ElementTree as ET

import pytest

from app.compiler import (
    CompileDocument,
    CompileLayer,
    CompileObject,
    CompileStitch,
    compile_svg,
)
from app.models import ThreadColor

SVG_NS = "{http://www.w3.org/2000/svg}"


def sample_document() -> CompileDocument:
    return CompileDocument(
        width_mm=100,
        height_mm=100,
        layers=[
            CompileLayer(
                id="layer-1",
                name="red",
                objects=[
                    CompileObject(
                        id="obj-1",
                        path_d="M 10,10 L 50,10 L 50,40 L 10,40 Z",
                        color=ThreadColor(hex="#c0392b"),
                        stitch=CompileStitch(type="fill"),
                    )
                ],
            ),
            CompileLayer(
                id="layer-2",
                name="blue",
                objects=[
                    CompileObject(
                        id="obj-2",
                        path_d="M 60,10 L 90,10 L 90,40 L 60,40 Z",
                        color=ThreadColor(hex="#2980b9"),
                    )
                ],
            ),
        ],
    )


def test_compile_svg_structure():
    svg = compile_svg(sample_document())
    root = ET.fromstring(svg)
    assert root.tag == f"{SVG_NS}svg"
    assert root.attrib["width"] == "377.952756"
    paths = root.findall(f".//{SVG_NS}path")
    assert len(paths) == 2
    assert paths[0].attrib["style"] == "fill:#c0392b;stroke:none"
    assert paths[1].attrib["style"] == "fill:#2980b9;stroke:none"


def test_compile_is_deterministic():
    assert compile_svg(sample_document()) == compile_svg(sample_document())


def test_compile_emits_inkstitch_params():
    doc = sample_document()
    doc.layers[0].objects[0].stitch = CompileStitch(
        type="fill", angle_deg=45, row_spacing_mm=0.5, underlay=False
    )
    svg = compile_svg(doc)
    assert 'inkstitch:angle="45"' in svg
    assert 'inkstitch:row_spacing_mm="0.5"' in svg
    assert 'inkstitch:fill_underlay="false"' in svg
    assert 'xmlns:inkstitch="http://inkstitch.org/namespace"' in svg


def test_compile_running_style():
    doc = sample_document()
    doc.layers[0].objects[0].stitch = CompileStitch(type="running")
    svg = compile_svg(doc)
    assert "fill:none;stroke:#c0392b;stroke-width:0.4" in svg


def test_compile_satin_marks_column():
    doc = sample_document()
    doc.layers[0].objects[0].path_d = "M 10,10 L 10,50 M 30,10 L 30,50"
    doc.layers[0].objects[0].stitch = CompileStitch(type="satin")
    svg = compile_svg(doc)
    assert 'inkstitch:satin_column="true"' in svg
    assert "fill:none;stroke:#c0392b" in svg


def test_compile_rejects_script_in_path():
    doc = sample_document()
    doc.layers[0].objects[0].path_d = 'M 0,0"/><script>alert(1)</script>'
    with pytest.raises(ValueError):
        compile_svg(doc)


def test_compile_rejects_empty_layers():
    with pytest.raises(ValueError):
        compile_svg(CompileDocument(layers=[]))
