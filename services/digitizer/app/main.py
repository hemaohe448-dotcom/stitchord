"""Stitchord 打版服务（Phase 0）：格式读取、预览计划、导出、静态校验。"""

from __future__ import annotations

import os
import tempfile
from pathlib import Path

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response

from .convert import read_stitch_plan, write_stitch_file
from .models import ExportRequest, StitchPlan, ValidationReport
from .validation import validate_plan

MAX_UPLOAD_BYTES = 25 * 1024 * 1024
ALLOWED_EXTENSIONS = {".dst", ".pes", ".exp", ".jef", ".vp3", ".xxx"}

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


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "service": "digitizer", "version": "0.1.0"}


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
