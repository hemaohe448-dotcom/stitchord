"""Probe vtracer output format on a synthetic flat-colour image."""

from __future__ import annotations

import inspect
import os

import vtracer
from PIL import Image, ImageDraw

OUT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "artifacts", "vectorize"))
os.makedirs(OUT, exist_ok=True)

image = Image.new("RGB", (200, 120), "white")
draw = ImageDraw.Draw(image)
draw.rectangle((20, 20, 80, 80), fill="#c0392b")
draw.ellipse((110, 25, 170, 85), fill="#2980b9")
draw.rectangle((20, 95, 120, 105), fill="#1a202c")
src = os.path.join(OUT, "probe.png")
image.save(src)

print("signature:", inspect.signature(vtracer.convert_image_to_svg_py))
dst = os.path.join(OUT, "probe.svg")
vtracer.convert_image_to_svg_py(
    src,
    dst,
    colormode="color",
    hierarchical="stacked",
    mode="spline",
    filter_speckle=4,
    color_precision=6,
    layer_difference=16,
)
print("svg bytes:", os.path.getsize(dst))
with open(dst, encoding="utf-8") as handle:
    text = handle.read()
print(text[:1200])
