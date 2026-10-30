from __future__ import annotations

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)

DOCUMENT = {
    "widthMm": 100,
    "heightMm": 100,
    "fabric": "woven",
    "name": "Order #1",
    "layers": [
        {
            "id": "layer-red",
            "name": "red",
            "objects": [
                {
                    "id": "obj-red",
                    "pathD": "M 10,10 L 50,10 L 50,40 L 10,40 Z",
                    "color": {"hex": "#c0392b"},
                    "stitch": {"type": "fill"},
                }
            ],
        }
    ],
}


def test_project_crud(tmp_path, monkeypatch):
    monkeypatch.setenv("STITCHORD_DB_PATH", str(tmp_path / "projects.db"))

    created = client.post(
        "/v1/projects",
        json={"name": "Order #1", "document": DOCUMENT},
    )
    assert created.status_code == 200, created.text
    project_id = created.json()["id"]

    listing = client.get("/v1/projects")
    assert listing.status_code == 200
    assert any(item["id"] == project_id for item in listing.json())

    fetched = client.get(f"/v1/projects/{project_id}")
    assert fetched.status_code == 200, fetched.text
    assert fetched.json()["document"]["name"] == "Order #1"

    updated = client.put(
        f"/v1/projects/{project_id}",
        json={"name": "Order #2", "document": DOCUMENT},
    )
    assert updated.status_code == 200
    assert client.get(f"/v1/projects/{project_id}").json()["name"] == "Order #2"

    stale = client.put(
        f"/v1/projects/{project_id}",
        json={
            "name": "stale",
            "document": DOCUMENT,
            "expectedUpdatedAt": "2000-01-01T00:00:00+00:00",
        },
    )
    assert stale.status_code == 409

    current = client.get(f"/v1/projects/{project_id}").json()["updatedAt"]
    fresh = client.put(
        f"/v1/projects/{project_id}",
        json={
            "name": "Order #3",
            "document": DOCUMENT,
            "expectedUpdatedAt": current,
        },
    )
    assert fresh.status_code == 200, fresh.text

    deleted = client.delete(f"/v1/projects/{project_id}")
    assert deleted.status_code == 204
    assert client.get(f"/v1/projects/{project_id}").status_code == 404
    assert client.delete(f"/v1/projects/{project_id}").status_code == 404


def test_project_rejects_invalid_document(tmp_path, monkeypatch):
    monkeypatch.setenv("STITCHORD_DB_PATH", str(tmp_path / "projects.db"))
    response = client.post(
        "/v1/projects",
        json={"name": "bad", "document": {"widthMm": 100, "heightMm": 100, "layers": []}},
    )
    assert response.status_code == 422
