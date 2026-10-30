from __future__ import annotations

import pytest
import pyembroidery
from fastapi.testclient import TestClient

from app import cache, inkstitch_adapter
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
def test_plan_stitch_count_close_to_dst(tmp_path):
    plan_response = client.post("/v1/digitize", json=DOCUMENT)
    export_response = client.post("/v1/digitize/export", json=DOCUMENT)
    assert plan_response.status_code == 200
    assert export_response.status_code == 200

    dst_path = tmp_path / "out.dst"
    dst_path.write_bytes(export_response.content)
    pattern = pyembroidery.read(str(dst_path))
    dst_stitches = sum(1 for stitch in pattern.stitches if stitch[2] == 0)
    # DST writers insert/merge boundary stitches at colour changes; allow <=3.
    difference = abs(plan_response.json()["stats"]["stitchCount"] - dst_stitches)
    assert difference <= 3, difference


@needs_inkstitch
def test_digitize_export_pes(tmp_path):
    response = client.post("/v1/digitize/export?format=pes", json=DOCUMENT)
    assert response.status_code == 200, response.text
    assert response.headers["X-Stitch-Format"] == "pes"
    path = tmp_path / "out.pes"
    path.write_bytes(response.content)
    pattern = pyembroidery.read(str(path))
    assert len(pattern.stitches) > 1000
    assert len(pattern.threadlist) >= 2


@needs_inkstitch
@pytest.mark.parametrize(
    ("fmt", "min_threads"),
    [("dst", 0), ("exp", 0), ("pes", 2), ("jef", 2), ("vp3", 2), ("xxx", 2)],
)
def test_machine_format_roundtrip(fmt, min_threads, tmp_path):
    response = client.post(f"/v1/digitize/export?format={fmt}", json=DOCUMENT)
    assert response.status_code == 200, response.text
    path = tmp_path / f"out.{fmt}"
    path.write_bytes(response.content)
    pattern = pyembroidery.read(str(path))
    assert len(pattern.stitches) > 1000
    assert len(pattern.threadlist) >= min_threads
    bounds = pattern.bounds()
    assert bounds[2] > bounds[0] and bounds[3] > bounds[1]


@needs_inkstitch
def test_export_rejects_outside_hoop():
    response = client.post(
        "/v1/digitize/export?hoop_width_mm=50&hoop_height_mm=100",
        json=DOCUMENT,
    )
    assert response.status_code == 422, response.text
    detail = response.json()["detail"]
    assert detail["message"]
    assert any(issue["code"] == "OUTSIDE_HOOP" for issue in detail["issues"])


@needs_inkstitch
def test_export_cache_hit():
    cache.clear()
    first = client.post("/v1/digitize/export?format=dst", json=DOCUMENT)
    second = client.post("/v1/digitize/export?format=dst", json=DOCUMENT)
    assert first.status_code == 200, first.text
    assert second.status_code == 200, second.text
    assert first.headers["X-Stitch-Cache"] == "miss"
    assert second.headers["X-Stitch-Cache"] == "hit"
    assert first.content == second.content


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
