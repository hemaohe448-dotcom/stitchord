from __future__ import annotations

import importlib.util
import io

import pytest
from fastapi.testclient import TestClient
from PIL import Image, ImageDraw

from app.compiler import compile_svg
from app.main import app
from app import inkstitch_adapter
from app.vectorize import vectorize_image

pytestmark = pytest.mark.skipif(
    importlib.util.find_spec("vtracer") is None,
    reason="vtracer not installed",
)

client = TestClient(app)


def sample_png() -> bytes:
    image = Image.new("RGB", (120, 80), "white")
    draw = ImageDraw.Draw(image)
    draw.rectangle((10, 10, 50, 60), fill="#c0392b")
    draw.ellipse((65, 15, 105, 55), fill="#2980b9")
    buffer = io.BytesIO()
    image.save(buffer, format="PNG")
    return buffer.getvalue()


def blue_background_png() -> bytes:
    image = Image.new("RGB", (120, 80), "#1e3a8a")
    draw = ImageDraw.Draw(image)
    draw.rectangle((30, 25, 90, 55), fill="#c0392b")
    buffer = io.BytesIO()
    image.save(buffer, format="PNG")
    return buffer.getvalue()


def test_vectorize_returns_mm_document():
    document = vectorize_image(sample_png(), width_mm=100, max_colors=6)
    assert document.width_mm == 100
    assert document.height_mm == pytest.approx(66.667, abs=0.01)
    assert len(document.layers) >= 2
    colors = {layer.name for layer in document.layers}
    assert "#ffffff" not in colors
    assert compile_svg(document).startswith("<?xml")


def test_vectorize_endpoint():
    response = client.post(
        "/v1/vectorize",
        files={"file": ("sample.png", sample_png(), "image/png")},
        data={"width_mm": "100", "max_colors": "6", "remove_background": "true"},
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["document"]["widthMm"] == 100
    assert body["stats"]["layers"] >= 2
    assert body["stats"]["paths"] >= 2
    assert body["document"]["unit"] == "mm" if "unit" in body["document"] else True


def test_vectorize_rejects_unknown_type():
    response = client.post(
        "/v1/vectorize",
        files={"file": ("sample.gif", b"GIF89a", "image/gif")},
    )
    assert response.status_code == 415


def test_border_background_is_removed():
    document = vectorize_image(
        blue_background_png(), width_mm=100, max_colors=4, remove_background=True
    )
    colors = {layer.name for layer in document.layers}
    assert colors
    assert "#1e3a8a" not in colors


def test_photo_style_returns_document():
    document = vectorize_image(
        sample_png(), width_mm=100, max_colors=6, remove_background=False, style="photo"
    )
    assert len(document.layers) >= 1
    assert sum(len(layer.objects) for layer in document.layers) >= 1


def test_invalid_style_rejected():
    response = client.post(
        "/v1/vectorize",
        files={"file": ("sample.png", sample_png(), "image/png")},
        data={"style": "sketch"},
    )
    assert response.status_code == 422


@pytest.mark.skipif(
    not inkstitch_adapter.available(), reason="Ink/Stitch runtime not available"
)
def test_vectorized_document_digitizes(tmp_path):
    document = vectorize_image(sample_png(), width_mm=100, max_colors=6)
    svg_path = tmp_path / "design.svg"
    svg_path.write_text(compile_svg(document), encoding="utf-8")
    result = inkstitch_adapter.digitize_svg(svg_path, tmp_path / "design.dst")
    assert result.plan["stats"]["stitchCount"] > 100
    assert len(result.plan["colorBlocks"]) >= 2
    assert len(result.dst) > 1000
