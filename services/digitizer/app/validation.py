"""工业上机前的静态校验（Phase 0 最小集）。

规则全部来自机器/工艺约束，阈值集中在常量里，后续由 docs/05-production-quality.md 扩展。
注意：通过校验只代表“格式与几何无明显错误”，不代表已通过真实缝合验证。
"""

from __future__ import annotations

import math

from .models import StitchPlan, ValidationIssue, ValidationReport

# DST 单条记录最大位移 121 × 0.1 mm = 12.1 mm（pyembroidery DstWriter.py:7-8）。
# 物理机器可能允许更长，但为保证 DST 可编码，静态上限取 12.1 mm；更长应拆分或跳针。
MAX_STITCH_MM = 12.1
# 低于该长度的针迹在多数面料上会堆线，通常应合并或删除。
MIN_STITCH_MM = 0.5
# 单色块针数上限的告警阈值（经验值，后续按机型配置）。
WARN_BLOCK_STITCHES = 50_000


def _dist(a, b) -> float:
    return math.hypot(a.x - b.x, a.y - b.y)


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

    width = plan.bounds.max_x - plan.bounds.min_x
    height = plan.bounds.max_y - plan.bounds.min_y
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

    ok = not any(issue.severity == "error" for issue in issues)
    return ValidationReport(ok=ok, issues=issues)
