"""Compare a StitchPlan JSON (mm, document coords) with a DST readback (0.1 mm, centered)."""

from __future__ import annotations

import json
import sys

import pyembroidery


def main(plan_path: str, dst_path: str) -> int:
    with open(plan_path, encoding="utf-8") as handle:
        plan = json.load(handle)
    pattern = pyembroidery.read(dst_path)

    px = [s for block in plan["colorBlocks"] for s in block["stitches"] if s["command"] == "STITCH"]
    dst_all = [(x / 10.0, y / 10.0, c) for x, y, c in pattern.stitches]
    dst = [(x, y) for x, y, c in dst_all if c == 0]
    print("plan stitches", len(px), "dst stitches", len(dst))

    # DST is centered on the design bbox; align plan bbox center to 0.
    cx = (plan["bounds"]["minX"] + plan["bounds"]["maxX"]) / 2
    cy = (plan["bounds"]["minY"] + plan["bounds"]["maxY"]) / 2
    aligned = [(round((s["x"] - cx) * 10) / 10, round((s["y"] - cy) * 10) / 10) for s in px]
    dst_rounded = [(round(x * 10) / 10, round(y * 10) / 10) for x, y in dst]

    # Find the first divergence with a simple one-stitch lookahead.
    i = j = 0
    while i < len(aligned) and j < len(dst_rounded):
        if aligned[i] == dst_rounded[j]:
            i += 1
            j += 1
            continue
        print("diverge at plan", i, aligned[i], "dst", j, dst_rounded[j])
        print("plan window", aligned[max(0, i - 2): i + 4])
        print("dst  window", dst_rounded[max(0, j - 2): j + 4])
        return 1
    print("prefix matched; remaining plan", len(aligned) - i, "dst", len(dst_rounded) - j)
    print("plan tail", aligned[-3:])
    print("dst tail", dst_rounded[-3:])
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1], sys.argv[2]))

