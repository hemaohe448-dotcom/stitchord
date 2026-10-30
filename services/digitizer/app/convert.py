"""pyembroidery ↔ StitchPlan 转换。

坐标：pyembroidery 内部单位为 0.1 mm，契约单位为 mm。
命令常量来自 pyembroidery 1.5.1 实测（见 docs/research/pyembroidery-notes.md），
禁止凭记忆修改；新增格式前先写探针测试。
"""

from __future__ import annotations

import os
import tempfile
from pathlib import Path

import pyembroidery

from .models import (
    Bounds,
    ColorBlock,
    Stitch,
    StitchPlan,
    StitchStats,
    ThreadColor,
)

# 实测值：STITCH=0, JUMP=1, TRIM=2, STOP=3, END=4, COLOR_CHANGE=5, NEEDLE_AT=177
_COMMAND_TO_NAME: dict[int, str] = {
    pyembroidery.STITCH: "STITCH",
    pyembroidery.JUMP: "JUMP",
    pyembroidery.TRIM: "TRIM",
    pyembroidery.STOP: "STOP",
    pyembroidery.END: "END",
    pyembroidery.COLOR_CHANGE: "COLOR_CHANGE",
    pyembroidery.NEEDLE_AT: "NEEDLE_AT",
}
_NAME_TO_COMMAND: dict[str, int] = {v: k for k, v in _COMMAND_TO_NAME.items()}

# DST 不携带颜色；按常见 12 色绣线序列回填，仅用于预览，不代表真实线色。
_DEFAULT_PALETTE = [
    "#1b1b1b", "#ffffff", "#c0392b", "#e67e22", "#f1c40f", "#2e7d32",
    "#16a085", "#2980b9", "#5b2c6f", "#8e44ad", "#d35400", "#7f8c8d",
]

_WRITERS = {
    "dst": "write_dst",
    "exp": "write_exp",
    "jef": "write_jef",
    "pes": "write_pes",
    "vp3": "write_vp3",
    "xxx": "write_xxx",
}


def _hex(value: object, fallback: str) -> str:
    if isinstance(value, str) and value.startswith("#") and len(value) == 7:
        return value.lower()
    if isinstance(value, int):
        return f"#{value & 0xFFFFFF:06x}"
    return fallback


def _threads(pattern: pyembroidery.EmbPattern) -> list[ThreadColor]:
    threads: list[ThreadColor] = []
    for index, thread in enumerate(pattern.threadlist or []):
        fallback = _DEFAULT_PALETTE[index % len(_DEFAULT_PALETTE)]
        threads.append(
            ThreadColor(
                hex=_hex(thread.get("color"), fallback),
                name=thread.get("name") or None,
                brand=thread.get("brand") or None,
                code=thread.get("code") or thread.get("chart") or None,
            )
        )
    return threads


def read_stitch_plan(path: str | Path) -> StitchPlan:
    """读取任意 pyembroidery 支持的格式并归一化为 StitchPlan。"""
    pattern = pyembroidery.read(str(path))
    if pattern is None or not pattern.stitches:
        raise ValueError("文件中没有可读取的针迹")

    threads = _threads(pattern)
    blocks: list[ColorBlock] = []
    current: list[Stitch] = []
    block_index = 0

    def flush() -> None:
        nonlocal block_index, current
        if not current:
            return
        color = threads[block_index] if block_index < len(threads) else ThreadColor(
            hex=_DEFAULT_PALETTE[block_index % len(_DEFAULT_PALETTE)]
        )
        blocks.append(
            ColorBlock(id=f"cb-{block_index + 1}", color=color, stitches=current)
        )
        block_index += 1
        current = []

    for raw in pattern.stitches:
        x, y, command = raw[0], raw[1], raw[2]
        name = _COMMAND_TO_NAME.get(int(command), "UNKNOWN")
        if name == "COLOR_CHANGE":
            # 色块边界即换色：契约用 colorBlocks 表达换色，不再重复存 COLOR_CHANGE 针。
            flush()
            continue
        current.append(Stitch(x=x / 10.0, y=y / 10.0, command=name))  # type: ignore[arg-type]
    flush()

    all_stitches = [s for block in blocks for s in block.stitches]
    xs = [s.x for s in all_stitches]
    ys = [s.y for s in all_stitches]
    bounds = Bounds(
        min_x=round(min(xs), 3),
        min_y=round(min(ys), 3),
        max_x=round(max(xs), 3),
        max_y=round(max(ys), 3),
    )

    def count(name: str) -> int:
        return sum(1 for s in all_stitches if s.command == name)

    stats = StitchStats(
        stitch_count=count("STITCH"),
        jump_count=count("JUMP"),
        trim_count=count("TRIM"),
        color_changes=max(0, len(blocks) - 1),
        color_blocks=len(blocks),
    )
    return StitchPlan(bounds=bounds, color_blocks=blocks, stats=stats)


def plan_to_pattern(plan: StitchPlan) -> pyembroidery.EmbPattern:
    pattern = pyembroidery.EmbPattern()
    for index, block in enumerate(plan.color_blocks):
        if index > 0:
            pattern.color_change()
        pattern.add_thread(
            {
                "color": block.color.hex,
                "name": block.color.name or block.color.hex,
                "brand": block.color.brand or "",
                "chart": block.color.code or "",
            }
        )
        for stitch in block.stitches:
            if stitch.command == "END":
                continue
            command = _NAME_TO_COMMAND.get(stitch.command, pyembroidery.STITCH)
            pattern.add_stitch_absolute(
                command, round(stitch.x * 10), round(stitch.y * 10)
            )
    pattern.end()
    return pattern


def write_stitch_file(plan: StitchPlan, fmt: str) -> bytes:
    """导出机器文件。pyembroidery 的 writer 只接受路径，故经临时文件中转。"""
    writer_name = _WRITERS.get(fmt)
    if writer_name is None:
        raise ValueError(f"不支持的导出格式: {fmt}")
    writer = getattr(pyembroidery, writer_name)
    pattern = plan_to_pattern(plan)

    work_dir = os.environ.get("STITCHORD_WORK_DIR") or tempfile.gettempdir()
    Path(work_dir).mkdir(parents=True, exist_ok=True)
    fd, path = tempfile.mkstemp(suffix=f".{fmt}", dir=work_dir)
    os.close(fd)
    try:
        writer(pattern, path)
        return Path(path).read_bytes()
    finally:
        try:
            os.unlink(path)
        except OSError:
            pass
