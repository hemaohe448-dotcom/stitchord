"""SQLite project storage (single-tenant; no auth)."""

from __future__ import annotations

import json
import os
import sqlite3
import tempfile
import uuid
from datetime import datetime, timezone
from pathlib import Path

_SCHEMA = """
CREATE TABLE IF NOT EXISTS projects (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    document TEXT NOT NULL,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
)
"""


def _db_path() -> Path:
    configured = os.environ.get("STITCHORD_DB_PATH")
    if configured:
        return Path(configured)
    return Path(tempfile.gettempdir()) / "stitchord.db"


def _connect() -> sqlite3.Connection:
    path = _db_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(path, timeout=10)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA journal_mode=WAL")
    connection.execute(_SCHEMA)
    return connection


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def create_project(name: str, document: dict) -> dict:
    project_id = str(uuid.uuid4())
    now = _now()
    with _connect() as connection:
        connection.execute(
            "INSERT INTO projects (id, name, document, created_at, updated_at) VALUES (?, ?, ?, ?, ?)",
            (project_id, name[:120], json.dumps(document), now, now),
        )
    return {"id": project_id, "name": name[:120], "updatedAt": now}


def list_projects() -> list[dict]:
    with _connect() as connection:
        rows = connection.execute(
            "SELECT id, name, updated_at FROM projects ORDER BY updated_at DESC"
        ).fetchall()
    return [
        {"id": row["id"], "name": row["name"], "updatedAt": row["updated_at"]}
        for row in rows
    ]


def get_project(project_id: str) -> dict | None:
    with _connect() as connection:
        row = connection.execute(
            "SELECT id, name, document, updated_at FROM projects WHERE id = ?",
            (project_id,),
        ).fetchone()
    if row is None:
        return None
    return {
        "id": row["id"],
        "name": row["name"],
        "document": json.loads(row["document"]),
        "updatedAt": row["updated_at"],
    }


def update_project(project_id: str, name: str, document: dict) -> bool:
    now = _now()
    with _connect() as connection:
        cursor = connection.execute(
            "UPDATE projects SET name = ?, document = ?, updated_at = ? WHERE id = ?",
            (name[:120], json.dumps(document), now, project_id),
        )
    return cursor.rowcount > 0


def delete_project(project_id: str) -> bool:
    with _connect() as connection:
        cursor = connection.execute(
            "DELETE FROM projects WHERE id = ?", (project_id,)
        )
    return cursor.rowcount > 0
