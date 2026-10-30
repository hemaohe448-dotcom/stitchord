"""工业上机前的静态校验（Phase 0 最小集）。

规则全部来自机器/工艺约束，阈值集中在常量里，后续由 docs/05-production-quality.md 扩展。
注意：通过校验只代表“格式与几何无明显错误”，不代表已通过真实缝合验证。
"""

from __future__ import annotations

import math

from .models import StitchPlan, StitchStats, ValidationIssue, ValidationReport

# DST 单条记录最大位移 121 × 0.1 mm = 12.1 mm（pyembroidery DstWriter.py:7-8）。
# 物理机器可能允许更长，但为保证 DST 可编码，静态上限取 12.1 mm；更长应拆分或跳针。
MAX_STITCH_MM = 12.1
# 低于该长度的针迹在多数面料上会堆线，通常应合并或删除。
MIN_STITCH_MM = 0.5
# 单色块针数上限的告警阈值（经验值，后续按机型配置）。
WARN_BLOCK_STITCHES = 50_000
# 跳针/剪线/换色过多的经验阈值，先作为 warning，不阻塞导出。
WARN_JUMP_RATIO = 0.25
WARN_TRIMS = 500
WARN_COLOR_BLOCKS = 16


def _dist(a, b) -> float:
    return math.hypot(a.x - b.x, a.y - b.y)


def computed_bounds(plan: StitchPlan) -> tuple[float, float, float, float] | None:
    """Bounds from the actual stitches; caller-supplied bounds are not trusted."""
    xs: list[float] = []
    ys: list[float] = []
    for block in plan.color_blocks:
        for stitch in block.stitches:
            if math.isfinite(stitch.x) and math.isfinite(stitch.y):
                xs.append(stitch.x)
                ys.append(stitch.y)
    if not xs:
        return None
    return min(xs), min(ys), max(xs), max(ys)


def computed_stats(plan: StitchPlan) -> StitchStats:
    stitch_count = 0
    jump_count = 0
    trim_count = 0
    for block in plan.color_blocks:
        for stitch in block.stitches:
            if stitch.command == "STITCH":
                stitch_count += 1
            elif stitch.command == "JUMP":
                jump_count += 1
            elif stitch.command == "TRIM":
                trim_count += 1
    return StitchStats(
        stitch_count=stitch_count,
        jump_count=jump_count,
        trim_count=trim_count,
        color_changes=max(len(plan.color_blocks) - 1, 0),
        color_blocks=len(plan.color_blocks),
    )


def validate_plan(plan: StitchPlan) -> ValidationReport:
    issues: list[ValidationIssue] = []

    if not plan.color_blocks:
        issues.append(
            ValidationIssue(
                code="EMPTY_PLAN",
                severity="error",
                message="没有任何颜色块 / 针迹",
            )
        )
        return ValidationReport(ok=False, issues=issues)

    total = 0
    jump_count = 0
    trim_count = 0
    for block in plan.color_blocks:
        if not block.stitches:
            issues.append(
                ValidationIssue(
                    code="EMPTY_BLOCK",
                    severity="error",
                    message="颜色块为空",
                    block_id=block.id,
                )
            )
            continue
        total += len(block.stitches)
        if len(block.stitches) > WARN_BLOCK_STITCHES:
            issues.append(
                ValidationIssue(
                    code="BLOCK_TOO_LARGE",
                    severity="warning",
                    message=f"颜色块针数 {len(block.stitches)} 过大，建议拆色块或分框",
                    block_id=block.id,
                )
            )

        previous = None
        for index, stitch in enumerate(block.stitches):
            if not math.isfinite(stitch.x) or not math.isfinite(stitch.y):
                issues.append(
                    ValidationIssue(
                        code="NON_FINITE_COORDINATE",
                        severity="error",
                        message="针迹坐标包含 NaN/Infinity",
                        block_id=block.id,
                        stitch_index=index,
                    )
                )
                previous = None
                continue
            if stitch.command in ("STITCH", "JUMP") and previous is not None:
                distance = _dist(previous, stitch)
                if stitch.command == "STITCH" and distance > MAX_STITCH_MM:
                    issues.append(
                        ValidationIssue(
                            code="STITCH_TOO_LONG",
                            severity="error",
                            message=f"针距 {distance:.2f} mm 超过 {MAX_STITCH_MM} mm",
                            block_id=block.id,
                            stitch_index=index,
                        )
                    )
                if stitch.command == "JUMP" and distance > MAX_STITCH_MM:
                    issues.append(
                        ValidationIssue(
                            code="JUMP_TOO_LONG",
                            severity="warning",
                            message=f"跳针 {distance:.2f} mm 超过 {MAX_STITCH_MM} mm，writer 可能需要拆分",
                            block_id=block.id,
                            stitch_index=index,
                        )
                    )
                if stitch.command == "STITCH" and 0 < distance < MIN_STITCH_MM:
                    issues.append(
                        ValidationIssue(
                            code="STITCH_TOO_SHORT",
                            severity="warning",
                            message=f"针距 {distance:.3f} mm 小于 {MIN_STITCH_MM} mm",
                            block_id=block.id,
                            stitch_index=index,
                        )
                    )
                if distance == 0 and stitch.command == "STITCH":
                    issues.append(
                        ValidationIssue(
                            code="ZERO_LENGTH_STITCH",
                            severity="warning",
                            message="零长度针迹",
                            block_id=block.id,
                            stitch_index=index,
                        )
                    )
            if stitch.command in ("STITCH", "JUMP"):
                previous = stitch
            if stitch.command == "JUMP":
                jump_count += 1
            elif stitch.command == "TRIM":
                trim_count += 1

    bounds = computed_bounds(plan)
    if bounds is None:
        issues.append(
            ValidationIssue(
                code="DEGENERATE_BOUNDS",
                severity="error",
                message="图案没有有效坐标",
            )
        )
    else:
        width = bounds[2] - bounds[0]
        height = bounds[3] - bounds[1]
        if width <= 0 or height <= 0:
            issues.append(
                ValidationIssue(
                    code="DEGENERATE_BOUNDS",
                    severity="error",
                    message="图案包围盒为空",
                )
            )
    if total == 0:
        issues.append(
            ValidationIssue(
                code="NO_STITCHES",
                severity="error",
                message="没有实际针迹",
            )
        )

    stitch_count = sum(
        1
        for block in plan.color_blocks
        for stitch in block.stitches
        if stitch.command == "STITCH"
    )
    if stitch_count and jump_count > max(50, stitch_count * WARN_JUMP_RATIO):
        issues.append(
            ValidationIssue(
                code="JUMP_RATIO_HIGH",
                severity="warning",
                message=f"跳针 {jump_count} 次，相对 {stitch_count} 针偏高，建议检查路径/分色",
            )
        )
    if trim_count > WARN_TRIMS:
        issues.append(
            ValidationIssue(
                code="TOO_MANY_TRIMS",
                severity="warning",
                message=f"剪线 {trim_count} 次，建议合并路径或调整顺序",
            )
        )
    if len(plan.color_blocks) > WARN_COLOR_BLOCKS:
        issues.append(
            ValidationIssue(
                code="TOO_MANY_COLOR_BLOCKS",
                severity="warning",
                message=f"{len(plan.color_blocks)} 个色块，换色/装夹成本高",
            )
        )

    ok = not any(issue.severity == "error" for issue in issues)
    return ValidationReport(ok=ok, issues=issues)


def validate_with_hoop(
    plan: StitchPlan,
    hoop_width_mm: float,
    hoop_height_mm: float,
    margin_mm: float = 5.0,
) -> ValidationReport:
    """Combine static rules with a hoop fit check (design is centred by the writer)."""
    base = validate_plan(plan)
    issues = list(base.issues)

    width = 0.0
    height = 0.0
    bounds = computed_bounds(plan)
    if bounds is not None:
        width = bounds[2] - bounds[0]
        height = bounds[3] - bounds[1]
    if width > hoop_width_mm or height > hoop_height_mm:
        issues.append(
            ValidationIssue(
                code="OUTSIDE_HOOP",
                severity="error",
                message=(
                    f"图案 {width:.1f}×{height:.1f} mm 超出绣框 "
                    f"{hoop_width_mm:.0f}×{hoop_height_mm:.0f} mm，需要分框或缩小"
                ),
            )
        )
    elif width > hoop_width_mm - margin_mm * 2 or height > hoop_height_mm - margin_mm * 2:
        issues.append(
            ValidationIssue(
                code="TIGHT_HOOP_MARGIN",
                severity="warning",
                message=(
                    f"图案 {width:.1f}×{height:.1f} mm 距绣框边不足 {margin_mm:.0f} mm，"
                    "夹持与走针空间偏小"
                ),
            )
        )

    ok = not any(issue.severity == "error" for issue in issues)
    return ValidationReport(ok=ok, issues=issues)
