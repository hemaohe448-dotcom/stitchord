"""Compile Stitchord document JSON into an Ink/Stitch-compatible SVG.

This module is pure Python (no Ink/Stitch import). The worker consumes its output.
Units: document geometry is mm; the SVG root is in px at 96 dpi, and a single
`scale(px_per_mm)` group maps mm coordinates to px. Ink/Stitch applies group
transforms (verified 2026-10-30).
"""

from __future__ import annotations

import re
from typing import Literal

from pydantic import Field

from .models import ContractModel, ThreadColor

PX_PER_MM = 96 / 25.4
_PATH_RE = re.compile(r"^[MmLlHhVvCcSsQqTtAaZz0-9eE+\-.,\s]+$")
_ID_RE = re.compile(r"^[A-Za-z0-9_-]{1,64}$")


class CompileStitch(ContractModel):
    type: Literal["fill", "running", "satin"] = "fill"
    angle_deg: float | None = Field(default=None, ge=-180, le=180)
    row_spacing_mm: float | None = Field(default=None, ge=0.1, le=2.0)
    underlay: bool | None = None
    running_width_mm: float = Field(default=0.4, ge=0.1, le=2.0)


class CompileObject(ContractModel):
    id: str
    path_d: str
    color: ThreadColor
    stitch: CompileStitch = CompileStitch()


class CompileLayer(ContractModel):
    id: str
    name: str | None = None
    objects: list[CompileObject]


class CompileDocument(ContractModel):
    width_mm: float = 100.0
    height_mm: float = 100.0
    layers: list[CompileLayer]


def _validate(doc: CompileDocument) -> None:
    if not doc.layers:
        raise ValueError("document has no layers")
    for layer in doc.layers:
        if not _ID_RE.match(layer.id):
            raise ValueError(f"invalid layer id: {layer.id!r}")
        if not layer.objects:
            raise ValueError(f"layer {layer.id} has no objects")
        for obj in layer.objects:
            if not _ID_RE.match(obj.id):
                raise ValueError(f"invalid object id: {obj.id!r}")
            if not obj.path_d.strip():
                raise ValueError(f"object {obj.id} has empty path")
            if not _PATH_RE.match(obj.path_d):
                raise ValueError(f"object {obj.id} has unsupported path data")


def compile_svg(doc: CompileDocument) -> str:
    """Return a deterministic SVG string (no timestamp, fixed number formatting)."""
    _validate(doc)
    width_px = round(doc.width_mm * PX_PER_MM, 6)
    height_px = round(doc.height_mm * PX_PER_MM, 6)
    scale = round(PX_PER_MM, 9)

    parts = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        (
            f'<svg xmlns="http://www.w3.org/2000/svg" '
            f'xmlns:inkstitch="http://inkstitch.org/namespace" '
            f'width="{width_px}" height="{height_px}" '
            f'viewBox="0 0 {width_px} {height_px}">'
        ),
        f'<g transform="scale({scale})">',
    ]
    for layer in doc.layers:
        parts.append(f'<g id="{layer.id}">')
        for obj in layer.objects:
            if obj.stitch.type in ("running", "satin"):
                style = (
                    f"fill:none;stroke:{obj.color.hex};"
                    f"stroke-width:{obj.stitch.running_width_mm:g}"
                )
            else:
                style = f"fill:{obj.color.hex};stroke:none"
            params = _stitch_attributes(obj.stitch)
            parts.append(
                f'<path id="{obj.id}" d="{obj.path_d}" style="{style}"{params}/>'
            )
        parts.append("</g>")
    parts.append("</g>")
    parts.append("</svg>")
    return "\n".join(parts) + "\n"


def _stitch_attributes(stitch: CompileStitch) -> str:
    """Ink/Stitch namespaced params; names/units verified against source (P1)."""
    attributes: list[str] = []
    if stitch.type == "satin":
        attributes.append('inkstitch:satin_column="true"')
    if stitch.angle_deg is not None:
        attributes.append(f'inkstitch:angle="{stitch.angle_deg:g}"')
    if stitch.row_spacing_mm is not None:
        attributes.append(f'inkstitch:row_spacing_mm="{stitch.row_spacing_mm:g}"')
    if stitch.underlay is not None:
        value = "true" if stitch.underlay else "false"
        attributes.append(f'inkstitch:fill_underlay="{value}"')
    return (" " + " ".join(attributes)) if attributes else ""
