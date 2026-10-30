"""Headless Ink/Stitch worker (Phase 1 adapter).

Input: an SVG document produced by the Stitchord compiler (flat paths/layers).
Output: StitchPlan v1.0 JSON (mm) and a machine file (DST by default).

This module intentionally imports Ink/Stitch internals. It must run inside the
pinned worker image; see docs/research/inkstitch-headless.md.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
from typing import Iterable

# Must be set before importing lib.elements: avoids user-dir cache writes/locks.
import lib.utils.settings as inkstitch_settings

inkstitch_settings.global_settings._settings["cache_size"] = 0

import inkex  # noqa: E402
from lib import output  # noqa: E402
from lib.elements import node_to_elements  # noqa: E402
from lib.stitch_plan.stitch_plan import stitch_groups_to_stitch_plan  # noqa: E402

SVG_NS = "http://www.w3.org/2000/svg"
PX_PER_MM = 96 / 25.4


def _iter_leaf_nodes(root) -> Iterable:
    for node in root.iter():
        if node is root:
            continue
        if len(node) == 0:
            yield node


def collect_stitch_groups(root):
    groups = []
    element_types = []
    for node in _iter_leaf_nodes(root):
        try:
            elements = node_to_elements(node)
        except Exception:  # unsupported leaf (e.g. metadata) is skipped
            continue
        for element in elements:
            element_types.append(type(element).__name__)
            groups.extend(element.embroider(None))
    return groups, element_types


def plan_to_contract(plan, dpi: float = 96.0) -> dict:
    px_per_mm = dpi / 25.4
    blocks = []
    points = []
    for index, block in enumerate(plan):
        color_obj = getattr(block, "color", None)
        digits = getattr(color_obj, "hex_digits", None)
        color = f"#{digits.lower()}" if digits else "#000000"
        stitches = []
        for stitch in block:
            x_mm = round(stitch.x / px_per_mm, 3)
            y_mm = round(stitch.y / px_per_mm, 3)
            points.append((x_mm, y_mm))
            if getattr(stitch, "trim", False):
                command = "TRIM"
            elif getattr(stitch, "jump", False):
                command = "JUMP"
            elif getattr(stitch, "stop", False):
                command = "STOP"
            else:
                command = "STITCH"
            stitches.append({"x": x_mm, "y": y_mm, "command": command})
        blocks.append(
            {
                "id": f"cb-{index + 1}",
                "color": {"hex": color},
                "stitches": stitches,
            }
        )

    xs = [point[0] for point in points] or [0]
    ys = [point[1] for point in points] or [0]
    commands = [stitch["command"] for block in blocks for stitch in block["stitches"]]
    return {
        "schemaVersion": "1.0",
        "unit": "mm",
        "bounds": {
            "minX": min(xs),
            "minY": min(ys),
            "maxX": max(xs),
            "maxY": max(ys),
        },
        "colorBlocks": blocks,
        "stats": {
            "stitchCount": commands.count("STITCH"),
            "jumpCount": commands.count("JUMP"),
            "trimCount": commands.count("TRIM"),
            "colorChanges": max(0, len(blocks) - 1),
            "colorBlocks": len(blocks),
        },
    }


def compile_svg(
    svg_path: Path, dst_path: Path, plan_path: Path | None, dpi: float
) -> dict:
    document = inkex.load_svg(str(svg_path))
    root = document.getroot()
    groups, element_types = collect_stitch_groups(root)
    if not groups:
        raise ValueError("no embroiderable elements found in SVG")

    plan = stitch_groups_to_stitch_plan(groups)
    output.write_embroidery_file(str(dst_path), plan, root, settings={"date": ""})

    contract = plan_to_contract(plan, dpi=dpi)
    if plan_path is not None:
        plan_path.write_text(
            json.dumps(contract, ensure_ascii=False, indent=2), encoding="utf-8"
        )

    with dst_path.open("rb") as handle:
        digest = hashlib.sha256(handle.read()).hexdigest()

    return {
        "dst": str(dst_path),
        "dstBytes": dst_path.stat().st_size,
        "dstSha256": digest,
        "plan": contract["stats"],
        "bounds": contract["bounds"],
        "elements": element_types,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Stitchord Ink/Stitch worker")
    parser.add_argument("--svg", required=True, type=Path)
    parser.add_argument("--dst", required=True, type=Path)
    parser.add_argument("--plan", type=Path)
    parser.add_argument("--dpi", type=float, default=96.0)
    args = parser.parse_args()

    args.dst.parent.mkdir(parents=True, exist_ok=True)
    if args.plan is not None:
        args.plan.parent.mkdir(parents=True, exist_ok=True)

    result = compile_svg(args.svg, args.dst, args.plan, args.dpi)
    print(json.dumps(result, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
