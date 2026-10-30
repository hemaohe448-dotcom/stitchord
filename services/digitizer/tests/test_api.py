from __future__ import annotations

from fastapi.testclient import TestClient

from app.convert import write_stitch_file
from app.main import app
from app.models import StitchPlan
from app.security import reset_rate_limiter

from .test_convert import sample_plan

client = TestClient(app)


def _dst_bytes() -> bytes:
    return write_stitch_file(sample_plan(), "dst")


def test_health():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_ready_reflects_runtime():
    response = client.get("/ready")
    from app import inkstitch_adapter

    assert response.status_code == (200 if inkstitch_adapter.available() else 503)


def test_preview_dst():
    response = client.post(
        "/v1/stitch/preview",
        files={"file": ("sample.dst", _dst_bytes(), "application/octet-stream")},
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["schemaVersion"] == "1.0"
    assert body["unit"] == "mm"
    assert body["stats"]["stitchCount"] == 5
    assert len(body["colorBlocks"]) == 2


def test_preview_rejects_unknown_extension():
    response = client.post(
        "/v1/stitch/preview",
        files={"file": ("evil.svg", b"<svg/>", "image/svg+xml")},
    )
    assert response.status_code == 415


def test_validate_endpoint():
    plan = sample_plan().model_dump(by_alias=True)
    response = client.post("/v1/stitch/validate", json=plan)
    assert response.status_code == 200, response.text
    assert response.json()["ok"] is True


def test_check_endpoint_flags_hoop():
    plan = sample_plan().model_dump(by_alias=True)
    response = client.post(
        "/v1/stitch/check",
        json={"plan": plan, "hoopWidthMm": 10, "hoopHeightMm": 10},
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["ok"] is False
    assert any(issue["code"] == "OUTSIDE_HOOP" for issue in body["issues"])


def test_worksheet_pdf():
    plan = sample_plan().model_dump(by_alias=True)
    response = client.post(
        "/v1/worksheet",
        json={
            "plan": plan,
            "projectName": "Two blocks",
            "fabric": "woven",
            "hoop": "100x100",
        },
    )
    assert response.status_code == 200, response.text
    assert response.headers["content-type"] == "application/pdf"
    assert response.content.startswith(b"%PDF")
    assert len(response.content) > 2000


def test_worksheet_accepts_chinese_name():
    plan = sample_plan().model_dump(by_alias=True)
    response = client.post(
        "/v1/worksheet",
        json={"plan": plan, "projectName": "订单 A-1024"},
    )
    assert response.status_code == 200, response.text
    assert response.content.startswith(b"%PDF")


def test_api_key_guard(monkeypatch):
    plan = sample_plan().model_dump(by_alias=True)
    monkeypatch.setenv("STITCHORD_API_KEY", "secret")
    denied = client.post("/v1/stitch/validate", json=plan)
    assert denied.status_code == 401
    allowed = client.post(
        "/v1/stitch/validate",
        json=plan,
        headers={"X-API-Key": "secret"},
    )
    assert allowed.status_code == 200
    assert client.get("/health").status_code == 200


def test_rate_limit(monkeypatch):
    plan = sample_plan().model_dump(by_alias=True)
    monkeypatch.setenv("STITCHORD_RATE_LIMIT", "1")
    reset_rate_limiter()
    try:
        assert client.post("/v1/stitch/validate", json=plan).status_code == 200
        assert client.post("/v1/stitch/validate", json=plan).status_code == 429
    finally:
        reset_rate_limiter()


def test_export_and_read_back():
    plan: StitchPlan = sample_plan()
    response = client.post(
        "/v1/stitch/export",
        json={"plan": plan.model_dump(by_alias=True), "format": "dst"},
    )
    assert response.status_code == 200, response.text
    assert len(response.content) > 0

    preview = client.post(
        "/v1/stitch/preview",
        files={"file": ("out.dst", response.content, "application/octet-stream")},
    )
    assert preview.status_code == 200, preview.text
    assert preview.json()["stats"]["stitchCount"] == 5
