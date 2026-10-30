"""Emit a satin-column SVG to verify the satin path."""

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
                id="layer-satin",
                objects=[
                    CompileObject(
                        id="obj-satin",
                        path_d="M 10,10 L 10,50 M 30,10 L 30,50",
                        color=ThreadColor(hex="#c0392b"),
                        stitch=CompileStitch(type="satin"),
                    )
                ],
            )
        ],
    )
    out_dir = os.path.abspath(
        os.path.join(os.path.dirname(__file__), "..", "..", "artifacts", "e2e")
    )
    os.makedirs(out_dir, exist_ok=True)
    path = os.path.join(out_dir, "satin.svg")
    with open(path, "w", encoding="utf-8") as handle:
        handle.write(compile_svg(document))
    print(path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
