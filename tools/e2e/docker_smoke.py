"""Smoke-test a running digitizer container: health + one real digitize."""

from __future__ import annotations

import json
import sys
import time
import urllib.request

BASE = "http://127.0.0.1:8000"

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


def wait_for_health(timeout: float = 60.0) -> None:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        try:
            with urllib.request.urlopen(f"{BASE}/health", timeout=3) as response:
                if response.status == 200:
                    print("health: ok")
                    return
        except Exception:
            time.sleep(1)
    raise SystemExit("container did not become healthy in time")


def main() -> None:
    wait_for_health()
    payload = json.dumps(DOCUMENT).encode("utf-8")
    request = urllib.request.Request(
        f"{BASE}/v1/digitize",
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=120) as response:
        plan = json.loads(response.read())
    stitches = plan["stats"]["stitchCount"]
    blocks = len(plan["colorBlocks"])
    print(f"digitize: {stitches} stitches / {blocks} blocks")
    if stitches <= 0 or blocks != 2:
        raise SystemExit("unexpected digitize result")
    print("worker image smoke: ok")


if __name__ == "__main__":
    main()
