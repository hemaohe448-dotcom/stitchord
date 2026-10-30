"""Image -> flat-colour vector document (Phase 3 baseline).

Pipeline: Pillow (resize + quantize) -> VTracer (SVG) -> path parsing/scaling ->
CompileDocument (mm). No ML model is involved yet; this is the deterministic
baseline that ML segmentation can later improve.
"""

from __future__ import annotations

import io
import math
import re
import tempfile
import xml.etree.ElementTree as ET
from pathlib import Path

from .compiler import CompileDocument, CompileLayer, CompileObject, CompileStitch
from .models import ThreadColor

SVG_NS = "{http://www.w3.org/2000/svg}"
_TOKEN = re.compile(r"([A-Za-z])|(-?(?:\d+\.?\d*|\.\d+)(?:[eE][+-]?\d+)?)")
_TRANSLATE = re.compile(r"translate\(\s*(-?[\d.]+)\s*[,\s]\s*(-?[\d.]+)\s*\)")
_PARAMS = {"M": 2, "L": 2, "H": 1, "V": 1, "C": 6, "S": 4, "Q": 4, "T": 2, "A": 7, "Z": 0}


def _hex(value: str) -> str:
    value = value.strip()
    if value.startswith("#"):
        value = value[1:]
    if len(value) == 3:
        value = "".join(ch * 2 for ch in value)
    if len(value) != 6:
        raise ValueError(f"unsupported fill colour: {value!r}")
    return f"#{value.lower()}"


def _is_light(hex_color: str, threshold: int = 242) -> bool:
    r = int(hex_color[1:3], 16)
    g = int(hex_color[3:5], 16)
    b = int(hex_color[5:7], 16)
    return r >= threshold and g >= threshold and b >= threshold


def _transform_path(d: str, scale: float, tx: float, ty: float) -> str:
    """Scale an absolute SVG path by `scale`, then translate by (tx, ty)."""
    tokens = _TOKEN.findall(d)
    flat = [token[0] or token[1] for token in tokens]
    out: list[str] = []
    i = 0
    command = ""
    while i < len(flat):
        token = flat[i]
        if token.isalpha():
            command = token
            i += 1
            if command in "Zz":
                out.append("Z")
                continue
        if not command:
            raise ValueError("path data does not start with a command")
        if command.islower():
            raise ValueError("relative path commands are not supported by the vectorizer")
        count = _PARAMS.get(command.upper())
        if count is None:
            raise ValueError(f"unsupported path command: {command}")
        if count == 0:
            out.append("Z")
            continue
        if i + count > len(flat):
            raise ValueError("truncated path data")
        values = [float(value) for value in flat[i:i + count]]
        i += count

        if command in ("H",):
            out.append(f"H {(values[0] + tx) * scale:.3f}")
        elif command in ("V",):
            out.append(f"V {(values[0] + ty) * scale:.3f}")
        elif command == "A":
            rx, ry, rotation, large, sweep, x, y = values
            out.append(
                f"A {rx * scale:.3f} {ry * scale:.3f} {rotation:g} "
                f"{int(large)} {int(sweep)} {(x + tx) * scale:.3f} {(y + ty) * scale:.3f}"
            )
        else:
            parts = []
            for index in range(0, count, 2):
                x = values[index] + tx
                y = values[index + 1] + ty
                parts.extend([f"{x * scale:.3f}", f"{y * scale:.3f}"])
            out.append(f"{command} {' '.join(parts)}")
    return " ".join(out)


def _parse_svg(svg_path: Path, scale: float, remove_background: bool) -> dict[str, list[str]]:
    root = ET.parse(svg_path).getroot()
    by_color: dict[str, list[str]] = {}
    for path in root.iter(f"{SVG_NS}path"):
        d = path.attrib.get("d")
        fill = path.attrib.get("fill") or ""
        if not d or not fill.startswith("#"):
            continue
        color = _hex(fill)
        if remove_background and _is_light(color):
            continue
        transform = _TRANSLATE.search(path.attrib.get("transform", ""))
        tx = float(transform.group(1)) if transform else 0.0
        ty = float(transform.group(2)) if transform else 0.0
        by_color.setdefault(color, []).append(_transform_path(d, scale, tx, ty))
    return by_color


def _strip_border_background(image, tolerance: int = 24):
    """Flood-fill the connected border colour, then composite on white.

    This removes solid-colour photo/scan backgrounds that are not white; the
    later near-white filter handles the composited pixels.
    """
    from PIL import Image, ImageDraw

    rgba = image.convert("RGBA")
    width, height = rgba.size
    for corner in (
        (0, 0),
        (width - 1, 0),
        (0, height - 1),
        (width - 1, height - 1),
    ):
        try:
            ImageDraw.floodfill(rgba, corner, (0, 0, 0, 0), thresh=tolerance)
        except (ValueError, TypeError):
            continue
    background = Image.new("RGBA", rgba.size, (255, 255, 255, 255))
    return Image.alpha_composite(background, rgba).convert("RGB")


def vectorize_image(
    data: bytes,
    width_mm: float = 100.0,
    max_colors: int = 8,
    remove_background: bool = True,
    style: str = "flat",
) -> CompileDocument:
    from PIL import Image, ImageDraw, ImageFilter
    import vtracer

    if not math.isfinite(width_mm) or not 1 <= width_mm <= 1000:
        raise ValueError("widthMm must be between 1 and 1000")
    if not 2 <= max_colors <= 16:
        raise ValueError("maxColors must be between 2 and 16")
    if style not in ("flat", "photo"):
        raise ValueError("style must be 'flat' or 'photo'")

    Image.MAX_IMAGE_PIXELS = 50_000_000
    image = Image.open(io.BytesIO(data)).convert("RGBA")
    if max(image.size) > 2000:
        image.thumbnail((2000, 2000), Image.Resampling.LANCZOS)
    if remove_background:
        image = _strip_border_background(image)
    else:
        background = Image.new("RGBA", image.size, (255, 255, 255, 255))
        image = Image.alpha_composite(background, image).convert("RGB")

    max_side = 1000
    if max(image.size) > max_side:
        ratio = max_side / max(image.size)
        image = image.resize(
            (max(1, round(image.width * ratio)), max(1, round(image.height * ratio))),
            Image.Resampling.LANCZOS,
        )

    if style == "photo":
        image = image.filter(ImageFilter.MedianFilter(3))
        image = image.filter(ImageFilter.GaussianBlur(0.6))

    quantized = image.quantize(colors=max_colors, method=Image.Quantize.MEDIANCUT, dither=Image.Dither.NONE)
    image = quantized.convert("RGB")

    height_mm = width_mm * image.height / image.width
    scale = width_mm / image.width

    work_dir = Path(tempfile.mkdtemp(prefix="stitchord-vectorize-"))
    try:
        png_path = work_dir / "source.png"
        svg_path = work_dir / "traced.svg"
        image.save(png_path)
        vtracer.convert_image_to_svg_py(
            str(png_path),
            str(svg_path),
            colormode="color",
            hierarchical="stacked",
            mode="spline",
            filter_speckle=4,
            color_precision=6,
            layer_difference=16,
        )
        by_color = _parse_svg(svg_path, scale, remove_background)
    finally:
        for path in work_dir.iterdir():
            try:
                path.unlink()
            except OSError:
                pass
        try:
            work_dir.rmdir()
        except OSError:
            pass

    if not by_color:
        raise ValueError("no vector shapes found")

    layers: list[CompileLayer] = []
    total_paths = 0
    for color, paths in by_color.items():
        objects = []
        for index, d in enumerate(paths[:200]):
            objects.append(
                CompileObject(
                    id=f"obj-{color[1:]}-{index + 1}",
                    path_d=d,
                    color=ThreadColor(hex=color),
                    stitch=CompileStitch(type="fill"),
                )
            )
        if objects:
            layers.append(CompileLayer(id=f"layer-{color[1:]}", name=color, objects=objects))
            total_paths += len(objects)

    if not layers:
        raise ValueError("no vector shapes found")

    return CompileDocument(
        width_mm=round(width_mm, 3),
        height_mm=round(height_mm, 3),
        fabric="woven",
        layers=layers,
    )
