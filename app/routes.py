"""Endpoint API lokal."""

from __future__ import annotations

import logging

from fastapi import APIRouter
from fastapi.responses import FileResponse
from starlette.background import BackgroundTask

from app.errors import AppError
from app.schemas import (
    DownloadRequest,
    ErrorResponse,
    HealthResponse,
    InfoRequest,
    InfoResponse,
)
from app.services.downloader import download_media, fetch_video_info
from app.utils.deps import dependency_status
from app.utils.files import cleanup_job_dir, file_size_bytes
from app.utils.validators import URLValidationError, validate_video_url

logger = logging.getLogger("fetchly.routes")

router = APIRouter(prefix="/api")


@router.get("/health", response_model=HealthResponse)
async def health() -> dict[str, str]:
    return {"status": "ok"}


@router.get("/deps")
def deps() -> dict[str, object]:
    return dependency_status()


@router.post(
    "/info",
    response_model=InfoResponse,
    responses={400: {"model": ErrorResponse}, 500: {"model": ErrorResponse}},
)
async def video_info(payload: InfoRequest) -> dict:
    try:
        target = validate_video_url(payload.url)
    except URLValidationError as exc:
        logger.warning("Validasi info gagal code=%s", exc.code)
        raise AppError(exc.code) from exc

    info = await fetch_video_info(target)
    logger.info(
        "Pemeriksaan info sukses platform=%s durasi=%ss",
        target.platform,
        info.get("duration", 0),
    )
    return info


@router.post(
    "/download",
    responses={
        200: {"content": {"application/octet-stream": {}}},
        400: {"model": ErrorResponse},
        500: {"model": ErrorResponse},
    },
)
async def download(payload: DownloadRequest) -> FileResponse:
    try:
        target = validate_video_url(payload.url)
    except URLValidationError as exc:
        logger.warning(
            "Validasi unduhan gagal format=%s code=%s", payload.format, exc.code
        )
        raise AppError(exc.code) from exc

    result = await download_media(target, payload.format, payload.quality)

    logger.info(
        "Unduhan sukses platform=%s format=%s kualitas=%s ukuran_mb=%.1f",
        target.platform,
        payload.format,
        payload.quality,
        file_size_bytes(result.path) / (1024 * 1024),
    )

    try:
        return FileResponse(
            path=result.path,
            media_type=result.media_type,
            filename=result.filename,
            headers={
                "Cache-Control": "no-store",
                "X-Content-Type-Options": "nosniff",
            },
            background=BackgroundTask(cleanup_job_dir, result.job_dir),
        )
    except Exception:
        cleanup_job_dir(result.job_dir)
        raise
