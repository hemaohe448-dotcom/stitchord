from __future__ import annotations

from pathlib import Path

from app.inkstitch_adapter import _repo_root_for


def test_repo_root_handles_shallow_container_path():
    # /app/app/inkstitch_adapter.py has only three parents in the image.
    root = _repo_root_for(Path("/app/app/inkstitch_adapter.py"))
    assert root.parent == root  # filesystem root
