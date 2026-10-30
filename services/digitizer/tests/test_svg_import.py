from __future__ import annotations

import importlib.util
import io

import pytest
from fastapi.testclient import TestClient

from app.compiler import compile_svg
from app.main import app
from app.svg_import import import_svg

pytestmark = pytest.mark.skipif(
    importlib.util.find_spec("svgelements") is None,
    reason="svgelements not installed",
)

client = TestClient(app)

SVG = """<svg xmlns="http://www.w3.org/2000/svg" width="200" height="100" viewBox="0 0 200 100">
  <g transform="translate(10,10)">
    <rect x="0" y="0" width="50" height="30" fill="#ff0000"/>
    <circle cx="100" cy="50" r="20" fill="#0000ff"/>
  </g>
  <path d="M 10 80 A 10 10 0 0 1 30 80 Q 40 70 50 80 Z" fill="#00ff00"/>
</svg>"""


def test_import_svg_builds_layers():
    document = import_svg(SVG.encode("utf-8"), width_mm=100)
    assert document.width_mm == 100
    assert document.height_mm == pytest.approx(50)
    assert len(document.layers) == 3
    assert sum(len(layer.objects) for layer in document.layers) == 3
    assert compile_svg(document).startswith("<?xml")


def test_import_svg_applies_group_transform():
    document = import_svg(SVG.encode("utf-8"), width_mm=100)
    red = next(layer for layer in document.layers if layer.name == "#ff0000")
    path = red.objects[0].path_d
    # viewBox 200 -> 100 mm means 0.5 scale; translated rect starts at 5 mm.
    assert "5" in path
    assert "30" in path


def test_import_svg_approximates_arcs():
    document = import_svg(SVG.encode("utf-8"), width_mm=100)
    green = next(layer for layer in document.layers if layer.name == "#00ff00")
    path = green.objects[0].path_d
    assert "A" not in path
    assert "C" in path


def test_import_svg_endpoint():
    response = client.post(
        "/v1/import/svg",
        files={"file": ("art.svg", SVG.encode("utf-8"), "image/svg+xml")},
        data={"width_mm": "100"},
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["stats"]["layers"] == 3
    assert body["document"]["widthMm"] == 100


def test_import_svg_rejects_other_type():
    response = client.post(
        "/v1/import/svg",
        files={"file": ("art.png", b"not svg", "image/png")},
    )
    assert response.status_code == 415


def test_import_svg_rejects_doctype_entity_and_script():
    payloads = [
        b'<!DOCTYPE svg [<!ENTITY x "boom">]><svg xmlns="http://www.w3.org/2000/svg"/>',
        b'<svg xmlns="http://www.w3.org/2000/svg"><script>alert(1)</script></svg>',
    ]
    for payload in payloads:
        response = client.post(
            "/v1/import/svg",
            files={"file": ("bad.svg", payload, "image/svg+xml")},
        )
        assert response.status_code == 422, response.text
