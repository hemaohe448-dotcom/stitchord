"""Compare a StitchPlan JSON (mm, document coords) with a DST readback (0.1 mm, centered)."""

from __future__ import annotations

import json
import math
import sys

import pyembroidery

TOL = 0.17  # DST quantizes to 0.1 mm; allow one unit plus rounding


def close(a: tuple[float, float], b: tuple[float, float]) -> bool:
    return math.hypot(a[0] - b[0], a[1] - b[1]) <= TOL


def main(plan_path: str, dst_path: str) -> int:
    with open(plan_path, encoding="utf-8") as handle:
        plan = json.load(handle)
    pattern = pyembroidery.read(dst_path)

    px = [
        s
        for block in plan["colorBlocks"]
        for s in block["stitches"]
        if s["command"] == "STITCH"
    ]
    dst = [(x / 10.0, y / 10.0) for x, y, c in pattern.stitches if c == 0]
    print("plan stitches", len(px), "dst stitches", len(dst))

    cx = (plan["bounds"]["minX"] + plan["bounds"]["maxX"]) / 2
    cy = (plan["bounds"]["minY"] + plan["bounds"]["maxY"]) / 2
    aligned = [(s["x"] - cx, s["y"] - cy) for s in px]

    i = j = 0
    extras: list[tuple[int, tuple[float, float]]] = []
    missing: list[tuple[int, tuple[float, float]]] = []
    while i < len(aligned) and j < len(dst):
        if close(aligned[i], dst[j]):
            i += 1
            j += 1
            continue
        if i + 1 < len(aligned) and close(aligned[i + 1], dst[j]):
            extras.append((i, aligned[i]))
            i += 1
            continue
        if j + 1 < len(dst) and close(aligned[i], dst[j + 1]):
            missing.append((j, dst[j]))
            j += 1
            continue
        print("unresolved at plan", i, aligned[i], "dst", j, dst[j])
        return 1

    print("plan-only stitches:", len(extras), extras[:5])
    print("dst-only stitches:", len(missing), missing[:5])
    print("tail plan", len(aligned) - i, "tail dst", len(dst) - j)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1], sys.argv[2]))
