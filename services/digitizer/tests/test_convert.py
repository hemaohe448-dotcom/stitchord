from __future__ import annotations

import pytest

from app.convert import plan_to_pattern, read_stitch_plan, write_stitch_file
from app.models import (
    Bounds,
    ColorBlock,
    Stitch,
    StitchPlan,
    StitchStats,
    ThreadColor,
)
from app.validation import computed_stats, validate_plan, validate_with_hoop


def sample_plan() -> StitchPlan:
    block1 = ColorBlock(
        id="cb-1",
        color=ThreadColor(hex="#c0392b", name="red"),
        stitches=[
            Stitch(x=0, y=0),
            Stitch(x=10, y=0),
            Stitch(x=10, y=10),
        ],
    )
    block2 = ColorBlock(
        id="cb-2",
        color=ThreadColor(hex="#2980b9", name="blue"),
        stitches=[
            Stitch(x=20, y=0),
            Stitch(x=20, y=10),
            Stitch(x=20, y=10, command="END"),
        ],
    )
    return StitchPlan(
        bounds=Bounds(min_x=0, min_y=0, max_x=20, max_y=10),
        color_blocks=[block1, block2],
        stats=StitchStats(
            stitch_count=5,
            jump_count=0,
            trim_count=0,
            color_changes=1,
            color_blocks=2,
        ),
    )


def test_dst_round_trip_preserves_geometry(tmp_path):
    plan = sample_plan()
    path = tmp_path / "sample.dst"
    path.write_bytes(write_stitch_file(plan, "dst"))

    loaded = read_stitch_plan(path)
    assert loaded.stats.stitch_count == 5
    assert loaded.stats.color_blocks == 2
    assert loaded.stats.color_changes == 1
    assert loaded.bounds.min_x == pytest.approx(0, abs=0.1)
    assert loaded.bounds.max_x == pytest.approx(20, abs=0.1)
    assert loaded.bounds.max_y == pytest.approx(10, abs=0.1)


def test_plan_to_pattern_keeps_stich_count():
    pattern = plan_to_pattern(sample_plan())
    stitched = [s for s in pattern.stitches if s[2] == 0]
    assert len(stitched) == 5


def test_validation_accepts_dst_limit():
    plan = sample_plan()
    plan.color_blocks[0].stitches = [Stitch(x=0, y=0), Stitch(x=12.1, y=0)]
    plan.color_blocks[1].stitches = [
        Stitch(x=20, y=0),
        Stitch(x=20, y=5),
        Stitch(x=20, y=5, command="END"),
    ]
    report = validate_plan(plan)
    assert report.ok, report.issues


def test_validation_flags_long_stitch():
    plan = sample_plan()
    plan.color_blocks[1].stitches.insert(1, Stitch(x=40, y=0))
    report = validate_plan(plan)
    assert not report.ok
    assert any(issue.code == "STITCH_TOO_LONG" for issue in report.issues)


def test_validation_accepts_sample():
    report = validate_plan(sample_plan())
    assert report.ok, report.issues


def test_export_rejects_unknown_format(tmp_path):
    with pytest.raises(ValueError):
        write_stitch_file(sample_plan(), "svg")


def test_hoop_outside_is_error():
    report = validate_with_hoop(sample_plan(), hoop_width_mm=10, hoop_height_mm=10)
    assert not report.ok
    assert any(issue.code == "OUTSIDE_HOOP" for issue in report.issues)


def test_hoop_tight_margin_is_warning():
    # 20 x 10 mm inside a 25 x 15 mm hoop: fits, but less than 2 * 5 mm margin.
    report = validate_with_hoop(sample_plan(), hoop_width_mm=25, hoop_height_mm=15)
    assert report.ok
    assert any(issue.code == "TIGHT_HOOP_MARGIN" for issue in report.issues)


def test_hoop_ignores_forged_bounds():
    plan = sample_plan().model_copy(deep=True)
    plan.bounds = type(plan.bounds)(min_x=0, min_y=0, max_x=1, max_y=1)
    plan.color_blocks[0].stitches[-1].x = 200
    report = validate_with_hoop(plan, hoop_width_mm=10, hoop_height_mm=10)
    assert not report.ok
    assert any(issue.code == "OUTSIDE_HOOP" for issue in report.issues)


def test_nan_is_rejected():
    plan = sample_plan().model_copy(deep=True)
    plan.color_blocks[0].stitches[0].x = float("nan")
    report = validate_plan(plan)
    assert not report.ok
    assert any(issue.code == "NON_FINITE_COORDINATE" for issue in report.issues)


def test_stats_are_recomputed():
    plan = sample_plan().model_copy(deep=True)
    plan.stats.stitch_count = 999_999
    stats = computed_stats(plan)
    assert stats.stitch_count != 999_999
    assert stats.stitch_count == sum(
        1 for block in plan.color_blocks for stitch in block.stitches if stitch.command == "STITCH"
    )


def test_long_jump_is_warned():
    plan = sample_plan().model_copy(deep=True)
    plan.color_blocks[0].stitches.append(Stitch(x=100, y=100, command="JUMP"))
    report = validate_plan(plan)
    assert any(issue.code == "JUMP_TOO_LONG" for issue in report.issues)
