"""Phase 1 spike: Ink/Stitch headless path -> stitch plan -> DST.

Run:
  PYTHONPATH=.research/repos/inkex;.research/repos/inkstitch \
  .condaenv/python.exe tools/spike/inkstitch_headless_v2.py

Not production code. Production worker will pin versions and expose a narrow API.
"""

from __future__ import annotations

import hashlib
import json
import os
import sys

import pyembroidery
from inkex import PathElement, Rectangle
from inkex.tester.svg import svg

# Disable Ink/Stitch disk cache: headless runs must not write user directories.
import lib.utils.settings as inkstitch_settings

inkstitch_settings.global_settings._settings["cache_size"] = 0

from lib import output  # noqa: E402
from lib.elements import node_to_elements  # noqa: E402
from lib.stitch_plan.stitch_plan import stitch_groups_to_stitch_plan  # noqa: E402

OUT_DIR = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "..", "artifacts", "p1")
)
os.makedirs(OUT_DIR, exist_ok=True)


def plan_to_contract(plan, dpi: float = 96.0) -> dict:
    """Project Ink/Stitch plan into StitchPlan v1.0 (mm, document coordinates)."""
    px_per_mm = dpi / 25.4
    blocks = []
    all_points = []
    for index, block in enumerate(plan):
        color_obj = getattr(block, "color", None)
        digits = getattr(color_obj, "hex_digits", None)
        color = f"#{digits.lower()}" if digits else "#000000"
        stitches = []
        for stitch in block:
            x_mm = round(stitch.x / px_per_mm, 3)
            y_mm = round(stitch.y / px_per_mm, 3)
            all_points.append((x_mm, y_mm))
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
                "color": {"hex": color.lower()},
                "stitches": stitches,
            }
        )

    xs = [point[0] for point in all_points] or [0]
    ys = [point[1] for point in all_points] or [0]
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


def build(svg_root, name: str, all_elements: bool = False) -> dict:
    nodes = list(svg_root) if all_elements else [svg_root[0]]
    groups = []
    element_types = []
    for node in nodes:
        for element in node_to_elements(node):
            element_types.append(type(element).__name__)
            groups.extend(element.embroider(None))
    plan = stitch_groups_to_stitch_plan(groups)

    dst_path = os.path.join(OUT_DIR, f"{name}.dst")
    output.write_embroidery_file(dst_path, plan, svg_root, settings={"date": ""})
    contract = plan_to_contract(plan)
    with open(os.path.join(OUT_DIR, f"{name}.plan.json"), "w", encoding="utf-8") as fh:
        json.dump(contract, fh, ensure_ascii=False, indent=2)
    with open(dst_path, "rb") as fh:
        digest = hashlib.sha256(fh.read()).hexdigest()
    return {
        "name": name,
        "elements": element_types,
        "blocks": len(contract["colorBlocks"]),
        "stitches": contract["stats"]["stitchCount"],
        "dst_bytes": os.path.getsize(dst_path),
        "sha256": digest,
        "bounds": contract["bounds"],
    }


def main() -> int:
    results = []

    root = svg()
    root.add(Rectangle(attrib={"width": "10", "height": "10"}))
    results.append(build(root, "rect"))

    # Arbitrary paths with two fill colors (verifies fill + color blocks).
    root2 = svg()
    root2.add(
        PathElement(
            attrib={
                "d": "M 10,10 L 50,10 L 50,40 L 10,40 Z",
                "style": "fill:#c0392b;stroke:none",
            }
        )
    )
    root2.add(
        PathElement(
            attrib={
                "d": "M 60,10 L 90,10 L 90,40 L 60,40 Z",
                "style": "fill:#2980b9;stroke:none",
            }
        )
    )
    results.append(build(root2, "two_colors", all_elements=True))

    for item in results:
        print(json.dumps(item, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
