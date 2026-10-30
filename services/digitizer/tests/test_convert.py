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
from app.validation import validate_plan


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
