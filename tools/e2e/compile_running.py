"""Emit a running-stitch SVG to verify the stroke path."""

from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "services", "digitizer")))

from app.compiler import (  # noqa: E402
    CompileDocument,
    CompileLayer,
    CompileObject,
    CompileStitch,
    compile_svg,
)
from app.models import ThreadColor  # noqa: E402


def main() -> int:
    document = CompileDocument(
        width_mm=100,
        height_mm=100,
        layers=[
            CompileLayer(
                id="layer-green",
                objects=[
                    CompileObject(
                        id="obj-green",
                        path_d="M 10,50 L 50,50 L 50,80",
                        color=ThreadColor(hex="#2e7d32"),
                        stitch=CompileStitch(type="running"),
                    )
                ],
            )
        ],
    )
    out_dir = os.path.abspath(
        os.path.join(os.path.dirname(__file__), "..", "..", "artifacts", "e2e")
    )
    os.makedirs(out_dir, exist_ok=True)
    path = os.path.join(out_dir, "running.svg")
    with open(path, "w", encoding="utf-8") as handle:
        handle.write(compile_svg(document))
    print(path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
