"""Emit two SVGs with different fill row spacing for parameter verification."""

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


def document(row_spacing: float | None) -> CompileDocument:
    stitch = CompileStitch(type="fill", row_spacing_mm=row_spacing)
    return CompileDocument(
        width_mm=100,
        height_mm=100,
        layers=[
            CompileLayer(
                id="layer-red",
                objects=[
                    CompileObject(
                        id="obj-red",
                        path_d="M 10,10 L 50,10 L 50,40 L 10,40 Z",
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
    for label, spacing in (("rows_default", None), ("rows_half", 0.5)):
        path = os.path.join(out_dir, f"{label}.svg")
        with open(path, "w", encoding="utf-8") as handle:
            handle.write(compile_svg(document(spacing)))
        print(path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
