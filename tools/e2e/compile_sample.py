"""Write the sample document as SVG using the production compiler (Python 3.14)."""

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
                id="layer-red",
                name="red",
                objects=[
                    CompileObject(
                        id="obj-red",
                        path_d="M 10,10 L 50,10 L 50,40 L 10,40 Z",
                        color=ThreadColor(hex="#c0392b", name="red"),
                        stitch=CompileStitch(type="fill"),
                    )
                ],
            ),
            CompileLayer(
                id="layer-blue",
                name="blue",
                objects=[
                    CompileObject(
                        id="obj-blue",
                        path_d="M 60,10 L 90,10 L 90,40 L 60,40 Z",
                        color=ThreadColor(hex="#2980b9", name="blue"),
                    )
                ],
            ),
        ],
    )
    out_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "artifacts", "e2e"))
    os.makedirs(out_dir, exist_ok=True)
    path = os.path.join(out_dir, "two_layers.svg")
    with open(path, "w", encoding="utf-8") as handle:
        handle.write(compile_svg(document))
    print(path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
