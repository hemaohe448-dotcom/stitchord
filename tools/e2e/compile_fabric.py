"""Emit fabric-preset variants for end-to-end comparison."""

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


def document(fabric: str, stitch: CompileStitch, path_d: str) -> CompileDocument:
    return CompileDocument(
        width_mm=100,
        height_mm=100,
        fabric=fabric,
        layers=[
            CompileLayer(
                id="layer-1",
                objects=[
                    CompileObject(
                        id="obj-1",
                        path_d=path_d,
                        color=ThreadColor(hex="#c0392b"),
                        stitch=stitch,
                    )
                ],
            )
        ],
    )


def main() -> int:
    out_dir = os.path.abspath(
        os.path.join(os.path.dirname(__file__), "..", "..", "artifacts", "e2e")
    )
    os.makedirs(out_dir, exist_ok=True)
    fill_path = "M 10,10 L 50,10 L 50,40 L 10,40 Z"
    satin_path = "M 10,10 L 10,50 M 30,10 L 30,50"
    cases = {
        "fabric_woven": document("woven", CompileStitch(type="fill"), fill_path),
        "fabric_knit": document("knit", CompileStitch(type="fill"), fill_path),
        "satin_woven": document("woven", CompileStitch(type="satin"), satin_path),
        "satin_knit": document("knit", CompileStitch(type="satin"), satin_path),
    }
    for name, doc in cases.items():
        path = os.path.join(out_dir, f"{name}.svg")
        with open(path, "w", encoding="utf-8") as handle:
            handle.write(compile_svg(doc))
        print(path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
