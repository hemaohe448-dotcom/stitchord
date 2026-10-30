"""SVG artwork -> CompileDocument (absolute M/L/C/Q/Z paths in mm)."""

from __future__ import annotations

import io

from .compiler import CompileDocument, CompileLayer, CompileObject, CompileStitch
from .models import ThreadColor
from .vectorize import _hex, _transform_path


def import_svg(data: bytes, width_mm: float = 100.0) -> CompileDocument:
    from svgelements import Path, Shape, SVG

    if width_mm <= 0:
        raise ValueError("widthMm must be positive")

    try:
        text = data.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise ValueError("SVG must be UTF-8") from exc

    try:
        svg = SVG.parse(io.StringIO(text))
    except Exception as exc:
        raise ValueError(f"could not parse SVG: {exc}") from exc

    viewbox = svg.viewbox
    if viewbox is not None and viewbox.width > 0 and viewbox.height > 0:
        base_x, base_y = float(viewbox.x), float(viewbox.y)
        base_w, base_h = float(viewbox.width), float(viewbox.height)
    else:
        base_x, base_y = 0.0, 0.0
        base_w = float(svg.width) if svg.width else 0.0
        base_h = float(svg.height) if svg.height else 0.0
    if base_w <= 0 or base_h <= 0:
        raise ValueError("SVG has no usable viewBox/width/height")

    scale = width_mm / base_w
    height_mm = base_h * scale
    by_color: dict[str, list[str]] = {}

    for element in svg.elements():
        if not isinstance(element, Shape):
            continue
        fill = str(element.fill) if element.fill is not None else "none"
        if not fill.startswith("#"):
            continue
        color = _hex(fill)
        path = Path(element)
        path.approximate_arcs_with_cubics()
        for subpath in path.as_subpaths():
            d = subpath.d(relative=False, smooth=False)
            if not d:
                continue
            by_color.setdefault(color, []).append(
                _transform_path(d, scale, -base_x, -base_y)
            )

    layers: list[CompileLayer] = []
    total = 0
    for color, paths in by_color.items():
        objects = [
            CompileObject(
                id=f"svg-{color[1:]}-{index + 1}",
                path_d=d,
                color=ThreadColor(hex=color),
                stitch=CompileStitch(type="fill"),
            )
            for index, d in enumerate(paths[:400])
        ]
        if objects:
            layers.append(CompileLayer(id=f"svg-{color[1:]}", name=color, objects=objects))
            total += len(objects)

    if not layers:
        raise ValueError("SVG has no filled paths")

    return CompileDocument(
        width_mm=round(width_mm, 3),
        height_mm=round(height_mm, 3),
        fabric="woven",
        layers=layers,
    )
