"""Fabric presets for fill/satin parameters.

Numeric values are taken from Roidery's MIT/Apache-licensed `fabric.rs`
(commit 0187f73, 2026-10-20), which encodes common digitizing practice.
Qualitative rules are cross-checked against Wilcom's public Auto Fabrics and
Quality documentation (see docs/reference/parameters.md).

This module is pure Python and has no Ink/Stitch import.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class FabricPreset:
    id: str
    label: str
    satin_density_mm: float
    pull_compensation_mm: float
    fill_row_spacing_mm: float
    fill_stitch_length_mm: float
    fill_underlay_spacing_mm: float
    heavy_underlay: bool


FABRICS: dict[str, FabricPreset] = {
    "woven": FabricPreset(
        "woven", "Woven (Cotton, Poplin)", 0.40, 0.20, 0.40, 3.0, 2.5, False
    ),
    "knit": FabricPreset(
        "knit", "Knit (T-Shirt, Jersey)", 0.42, 0.30, 0.42, 3.0, 2.0, True
    ),
    "pique": FabricPreset(
        "pique", "Piqué (Polo Shirt)", 0.40, 0.30, 0.40, 3.0, 2.0, True
    ),
    "terry": FabricPreset(
        "terry", "Terry (Towel)", 0.36, 0.35, 0.38, 3.0, 1.8, True
    ),
    "fleece": FabricPreset(
        "fleece", "Fleece", 0.38, 0.35, 0.40, 3.0, 2.0, True
    ),
    "denim": FabricPreset(
        "denim", "Denim, Canvas", 0.42, 0.15, 0.42, 3.5, 3.0, False
    ),
    "twill": FabricPreset(
        "twill", "Twill (Cap)", 0.40, 0.25, 0.40, 3.0, 2.5, False
    ),
    "leather": FabricPreset(
        "leather", "Leather, Vinyl", 0.50, 0.10, 0.50, 3.5, 3.5, False
    ),
}


def get_fabric(fabric_id: str | None) -> FabricPreset | None:
    if not fabric_id:
        return None
    preset = FABRICS.get(fabric_id.lower())
    if preset is None:
        known = ", ".join(sorted(FABRICS))
        raise ValueError(f"unknown fabric {fabric_id!r}; known: {known}")
    return preset
