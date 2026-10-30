from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app import inkstitch_adapter
from app.main import app

client = TestClient(app)

DOCUMENT = {
    "widthMm": 100,
    "heightMm": 100,
    "fabric": "woven",
    "layers": [
        {
            "id": "layer-red",
            "objects": [
                {
                    "id": "obj-red",
                    "pathD": "M 10,10 L 50,10 L 50,40 L 10,40 Z",
                    "color": {"hex": "#c0392b"},
                    "stitch": {"type": "fill"},
                }
            ],
        },
        {
            "id": "layer-blue",
            "objects": [
                {
                    "id": "obj-blue",
                    "pathD": "M 60,10 L 90,10 L 90,40 L 60,40 Z",
                    "color": {"hex": "#2980b9"},
                    "stitch": {"type": "fill"},
                }
            ],
        },
    ],
}


needs_inkstitch = pytest.mark.skipif(
    not inkstitch_adapter.available(),
    reason="Ink/Stitch runtime not available in this interpreter",
)


@needs_inkstitch
def test_digitize_two_colors():
    response = client.post("/v1/digitize", json=DOCUMENT)
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["schemaVersion"] == "1.0"
    assert len(body["colorBlocks"]) == 2
    assert [block["color"]["hex"] for block in body["colorBlocks"]] == [
        "#c0392b",
        "#2980b9",
    ]
    assert body["stats"]["stitchCount"] > 1000
    # Woven pull compensation (0.20 mm) expands the shape outward.
    assert 9.5 <= body["bounds"]["minX"] < 10.0
    assert 90.0 < body["bounds"]["maxX"] <= 90.5


@needs_inkstitch
def test_digitize_export_is_deterministic():
    first = client.post("/v1/digitize/export", json=DOCUMENT)
    second = client.post("/v1/digitize/export", json=DOCUMENT)
    assert first.status_code == 200, first.text
    assert second.status_code == 200, second.text
    assert first.content == second.content
    assert len(first.content) > 1000


@needs_inkstitch
def test_unknown_fabric_returns_422():
    document = dict(DOCUMENT)
    document["fabric"] = "silk"
    response = client.post("/v1/digitize", json=document)
    assert response.status_code == 422


def test_digitize_unavailable_returns_503(monkeypatch):
    monkeypatch.setattr(inkstitch_adapter, "available", lambda: False)
    response = client.post("/v1/digitize", json=DOCUMENT)
    assert response.status_code == 503
