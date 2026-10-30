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

from .fabric import get_fabric
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
    pull_compensation_mm: float | None = Field(default=None, ge=0.0, le=2.0)
    max_stitch_length_mm: float | None = Field(default=None, ge=0.5, le=12.0)
    underlay_spacing_mm: float | None = Field(default=None, ge=0.5, le=10.0)
    satin_density_mm: float | None = Field(default=None, ge=0.2, le=1.5)
    satin_heavy_underlay: bool | None = None


class CompileObject(ContractModel):
    id: str
    path_d: str
    color: ThreadColor
    stitch: CompileStitch = CompileStitch()
    translate_mm: tuple[float, float] | None = None


class CompileLayer(ContractModel):
    id: str
    name: str | None = None
    objects: list[CompileObject]


class CompileDocument(ContractModel):
    width_mm: float = 100.0
    height_mm: float = 100.0
    fabric: str | None = None
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
            stitch = _resolve_stitch(obj.stitch, doc.fabric)
            if stitch.type in ("running", "satin"):
                style = (
                    f"fill:none;stroke:{obj.color.hex};"
                    f"stroke-width:{stitch.running_width_mm:g}"
                )
            else:
                style = f"fill:{obj.color.hex};stroke:none"
            params = _stitch_attributes(stitch)
            transform = ""
            if obj.translate_mm is not None:
                dx, dy = obj.translate_mm
                transform = f' transform="translate({dx:g},{dy:g})"'
            parts.append(
                f'<path id="{obj.id}" d="{obj.path_d}" style="{style}"{transform}{params}/>'
            )
        parts.append("</g>")
    parts.append("</g>")
    parts.append("</svg>")
    return "\n".join(parts) + "\n"


def _resolve_stitch(stitch: CompileStitch, fabric_id: str | None) -> CompileStitch:
    """Apply fabric preset defaults to unset fields (explicit values win)."""
    fabric = get_fabric(fabric_id)
    if fabric is None:
        return stitch

    updates: dict[str, object] = {}
    if stitch.type == "fill":
        if stitch.row_spacing_mm is None:
            updates["row_spacing_mm"] = fabric.fill_row_spacing_mm
        if stitch.pull_compensation_mm is None:
            updates["pull_compensation_mm"] = fabric.pull_compensation_mm
        if stitch.max_stitch_length_mm is None:
            updates["max_stitch_length_mm"] = fabric.fill_stitch_length_mm
        if stitch.underlay is None:
            updates["underlay"] = True
        if stitch.underlay_spacing_mm is None:
            updates["underlay_spacing_mm"] = fabric.fill_underlay_spacing_mm
    elif stitch.type == "satin":
        if stitch.satin_density_mm is None:
            updates["satin_density_mm"] = fabric.satin_density_mm
        if stitch.pull_compensation_mm is None:
            updates["pull_compensation_mm"] = fabric.pull_compensation_mm
        if stitch.satin_heavy_underlay is None:
            updates["satin_heavy_underlay"] = fabric.heavy_underlay
    return stitch.model_copy(update=updates)


def _stitch_attributes(stitch: CompileStitch) -> str:
    """Ink/Stitch namespaced params; names/units verified against source (P1)."""
    attributes: list[str] = []
    if stitch.type == "satin":
        attributes.append('inkstitch:satin_column="true"')
    if stitch.angle_deg is not None:
        attributes.append(f'inkstitch:angle="{stitch.angle_deg:g}"')
    if stitch.type == "fill":
        if stitch.row_spacing_mm is not None:
            attributes.append(f'inkstitch:row_spacing_mm="{stitch.row_spacing_mm:g}"')
        if stitch.max_stitch_length_mm is not None:
            attributes.append(
                f'inkstitch:max_stitch_length_mm="{stitch.max_stitch_length_mm:g}"'
            )
        if stitch.underlay is not None:
            attributes.append(
                f'inkstitch:fill_underlay="{"true" if stitch.underlay else "false"}"'
            )
        if stitch.underlay_spacing_mm is not None:
            attributes.append(
                f'inkstitch:fill_underlay_row_spacing_mm="{stitch.underlay_spacing_mm:g}"'
            )
    if stitch.type == "satin":
        if stitch.satin_density_mm is not None:
            attributes.append(
                f'inkstitch:zigzag_spacing_mm="{stitch.satin_density_mm:g}"'
            )
        if stitch.satin_heavy_underlay:
            attributes.extend(
                [
                    'inkstitch:contour_underlay="true"',
                    'inkstitch:contour_underlay_inset_mm="0.4"',
                    'inkstitch:zigzag_underlay="true"',
                    'inkstitch:zigzag_underlay_spacing_mm="2"',
                ]
            )
        elif stitch.satin_heavy_underlay is False:
            attributes.append('inkstitch:center_walk_underlay="true"')
    if stitch.pull_compensation_mm is not None and stitch.type in ("fill", "satin"):
        attributes.append(
            f'inkstitch:pull_compensation_mm="{stitch.pull_compensation_mm:g}"'
        )
    return (" " + " ".join(attributes)) if attributes else ""
