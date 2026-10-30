"""Stitchord 打版服务（Phase 0）：格式读取、预览计划、导出、静态校验。"""

from __future__ import annotations

import os
import shutil
import tempfile
import threading
from pathlib import Path
from typing import Literal

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, Response

from . import cache, inkstitch_adapter
from .compiler import CompileDocument, compile_svg
from .convert import read_stitch_plan, write_stitch_file
from .models import (
    CheckRequest,
    ExportRequest,
    ProjectWrite,
    StitchPlan,
    ValidationReport,
    WorksheetRequest,
)
from . import storage
from .security import guard
from .svg_import import import_svg
from .validation import validate_plan, validate_with_hoop
from .vectorize import vectorize_image
from .worksheet import build_worksheet

MAX_UPLOAD_BYTES = 25 * 1024 * 1024
ALLOWED_EXTENSIONS = {".dst", ".pes", ".exp", ".jef", ".vp3", ".xxx"}
_DIGITIZE_LOCK = threading.Lock()

app = FastAPI(title="Stitchord Digitizer", version="0.1.0")

_origins = os.environ.get(
    "STITCHORD_CORS_ORIGINS",
    "http://localhost:5173,http://127.0.0.1:5173",
).split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[origin.strip() for origin in _origins if origin.strip()],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def request_guard(request, call_next):
    rejection = await guard(request)
    if rejection is not None:
        return rejection
    return await call_next(request)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "service": "digitizer", "version": "0.1.0"}


@app.get("/ready")
def ready():
    if not inkstitch_adapter.available():
        return JSONResponse(
            {"status": "not-ready", "reason": "Ink/Stitch import failed"},
            status_code=503,
        )
    return {"status": "ready", "service": "digitizer"}


def _require_suffix(filename: str) -> str:
    suffix = Path(filename or "").suffix.lower()
    if suffix not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=415,
            detail=f"不支持的文件类型 {suffix or '(none)'}；支持 {sorted(ALLOWED_EXTENSIONS)}",
        )
    return suffix


def _read_upload(upload: UploadFile) -> tuple[bytes, str]:
    suffix = _require_suffix(upload.filename or "")
    data = upload.file.read(MAX_UPLOAD_BYTES + 1)
    if len(data) > MAX_UPLOAD_BYTES:
        raise HTTPException(status_code=413, detail="文件超过 25 MB 限制")
    if not data:
        raise HTTPException(status_code=400, detail="空文件")
    return data, suffix


@app.post("/v1/stitch/preview", response_model=StitchPlan)
def preview_stitch(file: UploadFile = File(...)) -> StitchPlan:
    data, suffix = _read_upload(file)
    fd, path = tempfile.mkstemp(suffix=suffix)
    os.close(fd)
    try:
        Path(path).write_bytes(data)
        return read_stitch_plan(path)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except Exception as exc:  # pyembroidery 对损坏文件抛出的异常类型不稳定
        raise HTTPException(
            status_code=422, detail=f"无法解析该文件: {exc}"
        ) from exc
    finally:
        try:
            os.unlink(path)
        except OSError:
            pass


@app.post("/v1/stitch/validate", response_model=ValidationReport)
def validate(plan: StitchPlan) -> ValidationReport:
    return validate_plan(plan)


def _validated_document(payload: dict) -> CompileDocument:
    try:
        document = CompileDocument.model_validate(payload)
        compile_svg(document)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return document


@app.post("/v1/projects")
def create_project(request: ProjectWrite) -> dict:
    document = _validated_document(request.document)
    return storage.create_project(
        request.name,
        document.model_dump(by_alias=True, mode="json"),
    )


@app.get("/v1/projects")
def list_projects() -> list[dict]:
    return storage.list_projects()


@app.get("/v1/projects/{project_id}")
def get_project(project_id: str) -> dict:
    project = storage.get_project(project_id)
    if project is None:
        raise HTTPException(status_code=404, detail="project not found")
    return project


@app.put("/v1/projects/{project_id}")
def update_project(project_id: str, request: ProjectWrite) -> dict:
    document = _validated_document(request.document)
    if not storage.update_project(
        project_id,
        request.name,
        document.model_dump(by_alias=True, mode="json"),
    ):
        raise HTTPException(status_code=404, detail="project not found")
    return {"id": project_id, "name": request.name}


@app.delete("/v1/projects/{project_id}", status_code=204)
def delete_project(project_id: str) -> Response:
    if not storage.delete_project(project_id):
        raise HTTPException(status_code=404, detail="project not found")
    return Response(status_code=204)


@app.post("/v1/stitch/check", response_model=ValidationReport)
def check(request: CheckRequest) -> ValidationReport:
    return validate_with_hoop(
        request.plan, request.hoop_width_mm, request.hoop_height_mm
    )


@app.post("/v1/worksheet")
def worksheet(request: WorksheetRequest) -> Response:
    try:
        payload = build_worksheet(
            request.plan,
            project_name=request.project_name,
            fabric=request.fabric,
            hoop=request.hoop,
        )
    except Exception as exc:  # reportlab/Pillow errors vary
        raise HTTPException(status_code=422, detail=f"could not build worksheet: {exc}") from exc
    return Response(
        content=payload,
        media_type="application/pdf",
        headers={
            "Content-Disposition": 'attachment; filename="stitchord-worksheet.pdf"',
        },
    )


ALLOWED_IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".webp"}
MAX_IMAGE_BYTES = 15 * 1024 * 1024


@app.post("/v1/import/svg")
def import_svg_file(
    file: UploadFile = File(...),
    width_mm: float = Form(100.0),
) -> dict:
    suffix = Path(file.filename or "").suffix.lower()
    if suffix != ".svg":
        raise HTTPException(status_code=415, detail="expected an .svg file")
    data = file.file.read(MAX_IMAGE_BYTES + 1)
    if len(data) > MAX_IMAGE_BYTES:
        raise HTTPException(status_code=413, detail="SVG exceeds 15 MB")
    if not data:
        raise HTTPException(status_code=400, detail="empty SVG")
    try:
        document = import_svg(data, width_mm=width_mm)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return {
        "document": document.model_dump(by_alias=True),
        "stats": {
            "layers": len(document.layers),
            "paths": sum(len(layer.objects) for layer in document.layers),
            "widthMm": document.width_mm,
            "heightMm": document.height_mm,
        },
    }


@app.post("/v1/vectorize")
def vectorize(
    file: UploadFile = File(...),
    width_mm: float = Form(100.0),
    max_colors: int = Form(8),
    remove_background: bool = Form(True),
    style: str = Form("flat"),
    filter_speckle: int = Form(4),
    layer_difference: int = Form(16),
) -> dict:
    suffix = Path(file.filename or "").suffix.lower()
    if suffix not in ALLOWED_IMAGE_EXTENSIONS:
        raise HTTPException(
            status_code=415,
            detail=f"unsupported image type {suffix or '(none)'}; use png/jpg/webp",
        )
    data = file.file.read(MAX_IMAGE_BYTES + 1)
    if len(data) > MAX_IMAGE_BYTES:
        raise HTTPException(status_code=413, detail="image exceeds 15 MB")
    if not data:
        raise HTTPException(status_code=400, detail="empty image")

    try:
        document = vectorize_image(
            data,
            width_mm=width_mm,
            max_colors=max_colors,
            remove_background=remove_background,
            style=style,
            filter_speckle=filter_speckle,
            layer_difference=layer_difference,
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except Exception as exc:  # PIL/vtracer errors vary
        raise HTTPException(status_code=422, detail=f"could not vectorize image: {exc}") from exc

    return {
        "document": document.model_dump(by_alias=True),
        "stats": {
            "layers": len(document.layers),
            "paths": sum(len(layer.objects) for layer in document.layers),
            "widthMm": document.width_mm,
            "heightMm": document.height_mm,
        },
    }


def _digitize_document(document: CompileDocument, suffix: str = "dst"):
    if not inkstitch_adapter.available():
        raise HTTPException(
            status_code=503,
            detail="Ink/Stitch runtime unavailable; run this service on Python 3.11 with the pinned worker image",
        )
    key = cache.key_for(document, suffix)
    cached = cache.get(key)
    if cached is not None:
        return type(cached)(
            plan=cached.plan,
            dst=cached.dst,
            sha256=cached.sha256,
            writer=cached.writer,
            cached=True,
            groups_reused=cached.groups_reused,
        )
    work_dir: Path | None = None
    try:
        svg = compile_svg(document)
        work_dir = Path(tempfile.mkdtemp(prefix="stitchord-digitize-"))
        svg_path = work_dir / "design.svg"
        svg_path.write_text(svg, encoding="utf-8")
        with _DIGITIZE_LOCK:
            result = inkstitch_adapter.digitize_svg(
                svg_path, work_dir / f"design.{suffix}"
            )
        cache.put(key, result)
        return result
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    finally:
        if work_dir is not None:
            shutil.rmtree(work_dir, ignore_errors=True)


@app.post("/v1/digitize", response_model=StitchPlan)
def digitize(document: CompileDocument) -> StitchPlan:
    result = _digitize_document(document)
    return StitchPlan.model_validate(result.plan)


@app.post("/v1/digitize/export")
def digitize_export(
    document: CompileDocument,
    format: Literal["dst", "pes", "jef", "exp", "vp3", "xxx"] = "dst",
    hoop_width_mm: float | None = None,
    hoop_height_mm: float | None = None,
) -> Response:
    result = _digitize_document(document, suffix=format)
    plan = StitchPlan.model_validate(result.plan)
    report = validate_with_hoop(
        plan,
        hoop_width_mm if hoop_width_mm and hoop_width_mm > 0 else document.width_mm,
        hoop_height_mm if hoop_height_mm and hoop_height_mm > 0 else document.height_mm,
    )
    if not report.ok:
        raise HTTPException(
            status_code=422,
            detail={
                "message": "针迹未通过校验，拒绝导出",
                "issues": [issue.model_dump(by_alias=True) for issue in report.issues],
            },
        )
    return Response(
        content=result.dst,
        media_type="application/octet-stream",
        headers={
            "Content-Disposition": f'attachment; filename="stitchord.{format}"',
            "X-Stitch-Sha256": result.sha256,
            "X-Stitch-Format": format,
            "X-Stitch-Cache": "hit" if result.cached else "miss",
            "X-Stitch-Groups-Reused": str(result.groups_reused),
        },
    )


@app.post("/v1/stitch/export")
def export_stitch(request: ExportRequest) -> Response:
    report = validate_plan(request.plan)
    if not report.ok:
        raise HTTPException(
            status_code=422,
            detail={
                "message": "针迹未通过校验，拒绝导出",
                "issues": [issue.model_dump(by_alias=True) for issue in report.issues],
            },
        )
    try:
        payload = write_stitch_file(request.plan, request.format)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    return Response(
        content=payload,
        media_type="application/octet-stream",
        headers={
            "Content-Disposition": f'attachment; filename="stitchord.{request.format}"',
            "X-Stitch-Format": request.format,
        },
    )
