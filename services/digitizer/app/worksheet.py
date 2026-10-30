"""One-page production worksheet (PDF) for a StitchPlan.

English labels are intentional: ReportLab's built-in fonts do not embed CJK
glyphs, and the worksheet must render identically in the Linux worker image.
"""

from __future__ import annotations

import io
import math

from PIL import Image, ImageDraw
from reportlab.lib.pagesizes import A4
from reportlab.lib.utils import ImageReader
from reportlab.pdfgen import canvas

from .models import StitchPlan
from .validation import computed_bounds, computed_stats

PAGE_W, PAGE_H = A4
MARGIN = 40


def _render_preview(plan: StitchPlan, width: int = 1200, height: int = 700) -> Image.Image:
    image = Image.new("RGB", (width, height), "white")
    draw = ImageDraw.Draw(image)
    bw = max(plan.bounds.max_x - plan.bounds.min_x, 1e-6)
    bh = max(plan.bounds.max_y - plan.bounds.min_y, 1e-6)
    scale = min((width - 60) / bw, (height - 60) / bh)
    offset_x = (width - bw * scale) / 2 - plan.bounds.min_x * scale
    offset_y = (height - bh * scale) / 2 - plan.bounds.min_y * scale

    for block in plan.color_blocks:
        color = block.color.hex
        previous = None
        for stitch in block.stitches:
            point = (
                stitch.x * scale + offset_x,
                stitch.y * scale + offset_y,
            )
            if stitch.command == "STITCH" and previous is not None:
                draw.line([previous, point], fill=color, width=2)
            previous = point
    return image


def _thread_length_m(plan: StitchPlan) -> float:
    total = 0.0
    for block in plan.color_blocks:
        previous = None
        for stitch in block.stitches:
            point = (stitch.x, stitch.y)
            if stitch.command == "STITCH":
                if previous is not None:
                    total += math.hypot(point[0] - previous[0], point[1] - previous[1])
                previous = point
            elif stitch.command in ("JUMP", "COLOR_CHANGE"):
                previous = point
            elif stitch.command == "TRIM":
                previous = None
    return total / 1000.0


def build_worksheet(
    plan: StitchPlan,
    project_name: str = "Stitchord Design",
    fabric: str | None = None,
    hoop: str | None = None,
) -> bytes:
    buffer = io.BytesIO()
    pdf = canvas.Canvas(buffer, pagesize=A4)
    pdf.setTitle(project_name)
    pdf.setAuthor("Stitchord")

    y = PAGE_H - MARGIN
    pdf.setFont("Helvetica-Bold", 18)
    pdf.drawString(MARGIN, y, project_name)
    y -= 18
    pdf.setFont("Helvetica", 9)
    pdf.setFillColorRGB(0.35, 0.35, 0.35)
    pdf.drawString(MARGIN, y, "Production worksheet - starting parameters, test sew required")
    pdf.setFillColorRGB(0, 0, 0)

    preview = _render_preview(plan)
    preview_w = PAGE_W - MARGIN * 2
    preview_h = 280
    y -= preview_h + 14
    pdf.drawImage(
        ImageReader(preview),
        MARGIN,
        y,
        width=preview_w,
        height=preview_h,
        preserveAspectRatio=True,
        anchor="c",
    )

    bounds = computed_bounds(plan)
    if bounds is None:
        width = height = 0.0
    else:
        width = bounds[2] - bounds[0]
        height = bounds[3] - bounds[1]
    stats = computed_stats(plan)
    thread = _thread_length_m(plan)
    minutes = (
        stats.stitch_count / 700.0
        + stats.color_changes * 0.5
        + stats.trim_count * 0.1
    )

    rows = [
        ("Size", f"{width:.1f} x {height:.1f} mm"),
        ("Hoop", hoop or "-"),
        ("Fabric preset", fabric or "-"),
        ("Stitches", f"{stats.stitch_count:,}"),
        ("Jumps / trims", f"{stats.jump_count:,} / {stats.trim_count:,}"),
        ("Colour blocks", str(stats.color_blocks)),
        ("Colour changes", str(stats.color_changes)),
        ("Thread (upper, est.)", f"{thread * 1.3:.1f} m"),
        ("Sew time (est.)", f"{minutes:.1f} min @ 700 spm"),
    ]

    y -= 10
    pdf.setFont("Helvetica-Bold", 11)
    pdf.drawString(MARGIN, y, "Summary")
    y -= 16
    pdf.setFont("Helvetica", 9)
    for label, value in rows:
        pdf.setFillColorRGB(0.35, 0.35, 0.35)
        pdf.drawString(MARGIN, y, label)
        pdf.setFillColorRGB(0, 0, 0)
        pdf.drawString(MARGIN + 150, y, value)
        y -= 14

    y -= 8
    pdf.setFont("Helvetica-Bold", 11)
    pdf.drawString(MARGIN, y, "Thread sequence")
    y -= 16
    pdf.setFont("Helvetica", 9)
    for index, block in enumerate(plan.color_blocks, start=1):
        pdf.setFillColorRGB(0.35, 0.35, 0.35)
        pdf.drawString(MARGIN, y, f"{index}. {block.color.hex.upper()}")
        pdf.setFillColorRGB(0, 0, 0)
        pdf.drawString(
            MARGIN + 150,
            y,
            f"{len(block.stitches):,} stitches"
            + (f"  {block.color.name}" if block.color.name else ""),
        )
        pdf.setFillColorRGB(
            int(block.color.hex[1:3], 16) / 255,
            int(block.color.hex[3:5], 16) / 255,
            int(block.color.hex[5:7], 16) / 255,
        )
        pdf.rect(PAGE_W - MARGIN - 12, y - 2, 12, 10, fill=1, stroke=0)
        pdf.setFillColorRGB(0, 0, 0)
        y -= 14
        if y < MARGIN + 30:
            pdf.showPage()
            y = PAGE_H - MARGIN

    pdf.setFont("Helvetica", 7)
    pdf.setFillColorRGB(0.5, 0.5, 0.5)
    pdf.drawString(
        MARGIN,
        MARGIN,
        "Generated by Stitchord. Values are estimates; verify on the target machine and fabric.",
    )
    pdf.showPage()
    pdf.save()
    return buffer.getvalue()
