"""Pydantic 模型：与 packages/contracts/src/index.ts 一一对应（camelCase JSON）。"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field
from pydantic.alias_generators import to_camel

StitchCommand = Literal[
    "STITCH",
    "JUMP",
    "TRIM",
    "COLOR_CHANGE",
    "STOP",
    "END",
    "NEEDLE_AT",
    "UNKNOWN",
]


class ContractModel(BaseModel):
    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
        extra="forbid",
    )


class Stitch(ContractModel):
    x: float
    y: float
    command: StitchCommand = "STITCH"


class Bounds(ContractModel):
    min_x: float
    min_y: float
    max_x: float
    max_y: float


class ThreadColor(ContractModel):
    hex: str = Field(pattern=r"^#[0-9a-fA-F]{6}$")
    name: str | None = None
    brand: str | None = None
    code: str | None = None


class ColorBlock(ContractModel):
    id: str
    color: ThreadColor
    stitches: list[Stitch]


class StitchStats(ContractModel):
    stitch_count: int
    jump_count: int
    trim_count: int
    color_changes: int
    color_blocks: int


class StitchPlan(ContractModel):
    schema_version: Literal["1.0"] = "1.0"
    unit: Literal["mm"] = "mm"
    bounds: Bounds
    color_blocks: list[ColorBlock]
    stats: StitchStats


class ExportRequest(ContractModel):
    plan: StitchPlan
    format: Literal["dst", "exp", "jef", "pes", "vp3", "xxx"] = "dst"


class CheckRequest(ContractModel):
    plan: StitchPlan
    hoop_width_mm: float = Field(default=100.0, gt=0)
    hoop_height_mm: float = Field(default=100.0, gt=0)


class WorksheetRequest(ContractModel):
    plan: StitchPlan
    project_name: str = "Stitchord Design"
    fabric: str | None = None
    hoop: str | None = None


class Severity(str):
    ERROR = "error"
    WARNING = "warning"


class ValidationIssue(ContractModel):
    code: str
    severity: Literal["error", "warning"]
    message: str
    block_id: str | None = None
    stitch_index: int | None = None


class ValidationReport(ContractModel):
    ok: bool
    issues: list[ValidationIssue]
