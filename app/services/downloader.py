"""Layanan yt-dlp untuk mengambil informasi dan mengunduh media."""

from __future__ import annotations

import asyncio
import logging
import re
import threading
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

import yt_dlp
from fastapi.concurrency import run_in_threadpool
from yt_dlp.utils import DownloadCancelled, DownloadError, match_filter_func

from app.config import settings
from app.errors import AppError
from app.utils.deps import ffmpeg_available
from app.utils.files import (
    cleanup_job_dir,
    create_job_dir,
    file_size_bytes,
    find_media_file,
    pick_media_file,
    safe_filename,
)
from app.utils.validators import ValidatedVideoURL

logger = logging.getLogger("fetchly.downloader")

MediaFormat = Literal["mp4", "mp3"]
Quality = Literal["best", "1080", "720", "480", "360"]

MEDIA_TYPES = {
    "mp4": "video/mp4",
    "mp3": "audio/mpeg",
    "webm": "video/webm",
    "mkv": "video/x-matroska",
    "mov": "video/quicktime",
    "m4a": "audio/mp4",
}

_download_slots = asyncio.Semaphore(max(1, settings.max_parallel_jobs))


@dataclass(frozen=True, slots=True)
class DownloadResult:
    path: Path
    filename: str
    media_type: str
    job_dir: Path


class _YdlLogger:
    """Redam keluaran yt-dlp; error tetap dicatat lewat logger aplikasi."""

    def debug(self, message: str) -> None:
        logger.debug("yt-dlp: %s", message)

    def info(self, message: str) -> None:
        logger.debug("yt-dlp: %s", message)

    def warning(self, message: str) -> None:
        logger.debug("yt-dlp: %s", message)

    def error(self, message: str) -> None:
        logger.debug("yt-dlp: %s", message)


def _base_options(job_dir: Path | None = None) -> dict:
    options = {
        "quiet": True,
        "no_warnings": True,
        "noplaylist": True,
        "playlist_items": "1",
        "restrictfilenames": True,
        "windowsfilenames": True,
        "socket_timeout": 30,
        "retries": 3,
        "fragment_retries": 3,
        "max_filesize": settings.max_filesize_bytes,
        "noprogress": True,
        "cachedir": False,
        "logger": _YdlLogger(),
    }
    if job_dir is not None:
        options["outtmpl"] = str(job_dir / "%(id)s.%(ext)s")
    return options


def _clean_text(value: object, limit: int, fallback: str) -> str:
    text = " ".join(str(value or "").split())
    if not text:
        return fallback
    return text[:limit].strip()


def _normalize_thumbnail(info: dict) -> str:
    candidates: list[str] = []
    primary = info.get("thumbnail")
    if isinstance(primary, str) and primary:
        candidates.append(primary)
    for thumbnail in info.get("thumbnails") or []:
        if isinstance(thumbnail, dict):
            url = thumbnail.get("url")
            if isinstance(url, str) and url:
                candidates.append(url)

    for url in candidates:
        if url.startswith("//"):
            url = "https:" + url
        if url.startswith("http://"):
            url = "https://" + url[len("http://") :]
        if url.startswith("https://"):
            return url
    return ""


def _available_formats(info: dict) -> list[dict[str, int | str]]:
    heights: set[int] = set()
    for video_format in info.get("formats") or []:
        if not isinstance(video_format, dict):
            continue
        if video_format.get("vcodec") in (None, "none"):
            continue
        height = video_format.get("height")
        if isinstance(height, int) and height > 0:
            heights.add(height)

    return [
        {"quality": f"{height}p", "height": height}
        for height in (1080, 720, 480, 360)
        if height in heights
    ]


def _extract_info_sync(target: ValidatedVideoURL) -> dict:
    options = _base_options()
    options["skip_download"] = True

    try:
        with yt_dlp.YoutubeDL(options) as ydl:
            info = ydl.extract_info(target.url, download=False)
    except DownloadError as exc:
        raise _map_download_error(exc) from exc
    except AppError:
        raise
    except Exception as exc:  # noqa: BLE001 - jangan bocorkan detail ke klien
        logger.exception("Gagal mengambil informasi video.")
        raise AppError("INTERNAL_ERROR") from exc

    if not info:
        raise AppError("UNAVAILABLE")

    if info.get("_type") in {"playlist", "multi_video"}:
        entries = [entry for entry in (info.get("entries") or []) if entry]
        if not entries:
            raise AppError("UNAVAILABLE")
        info = entries[0]

    if info.get("is_live"):
        raise AppError("UNAVAILABLE")

    duration_value = info.get("duration")
    if isinstance(duration_value, (int, float)):
        if duration_value > settings.max_duration_seconds:
            raise AppError("TOO_LONG")
        duration = max(0, int(round(duration_value)))
    else:
        duration = 0

    return {
        "platform": target.platform,
        "title": _clean_text(info.get("title"), 300, "Video tanpa judul"),
        "uploader": _clean_text(
            info.get("uploader")
            or info.get("channel")
            or info.get("uploader_id"),
            150,
            "Tidak diketahui",
        ),
        "thumbnail": _normalize_thumbnail(info),
        "duration": duration,
        "formats": _available_formats(info),
    }


async def fetch_video_info(target: ValidatedVideoURL) -> dict:
    try:
        return await asyncio.wait_for(
            run_in_threadpool(_extract_info_sync, target),
            timeout=settings.info_timeout_seconds,
        )
    except asyncio.TimeoutError as exc:
        logger.warning(
            "Pemeriksaan info timeout platform=%s", target.platform
        )
        raise AppError("TIMEOUT") from exc
    except AppError as exc:
        logger.warning(
            "Pemeriksaan info gagal platform=%s code=%s",
            target.platform,
            exc.code,
        )
        raise
    except Exception as exc:  # noqa: BLE001
        logger.exception("Pemeriksaan info gagal tanpa terduga.")
        raise AppError("INTERNAL_ERROR") from exc


def _map_download_error(exc: Exception) -> AppError:
    message = str(exc)
    lowered = message.lower()

    if "batas waktu" in lowered or "timed out" in lowered or "timeout" in lowered:
        code = "TIMEOUT"
    elif "max-filesize" in lowered or "max filesize" in lowered or "larger than" in lowered:
        code = "TOO_LARGE"
    elif "does not pass filter" in lowered:
        code = "TOO_LONG"
    elif "ffmpeg" in lowered and any(
        phrase in lowered
        for phrase in ("not found", "not installed", "install", "not available")
    ):
        code = "FFMPEG_MISSING"
    elif any(
        phrase in lowered
        for phrase in (
            "not a bot",
            "sign in to confirm you're not a bot",
            "sign in to confirm you’re not a bot",
            "http error 403",
            "forbidden",
        )
    ):
        code = "INTERNAL_ERROR"
    elif any(
        phrase in lowered
        for phrase in (
            "private video",
            "video is private",
            "not available in your country",
            "not available in your region",
            "has been removed",
            "has been deleted",
            "does not exist",
            "http error 404",
            "this video is not available",
            "no video formats found",
            "uploader has not made this video available",
            "content isn't available",
            "content isn’t available",
        )
    ):
        code = "UNAVAILABLE"
    elif any(
        phrase in lowered
        for phrase in (
            "members-only",
            "members only",
            "join this channel",
            "channel's members",
            "channel’s members",
            "premium",
            "paid",
            "rental",
            "purchase",
            "age-restricted",
            "age restricted",
            "sign in",
            "login required",
        )
    ):
        code = "RESTRICTED"
    elif "video unavailable" in lowered:
        code = "UNAVAILABLE"
    elif "unsupported url" in lowered:
        code = "UNSUPPORTED_PLATFORM"
    elif "requested format is not available" in lowered:
        code = "INTERNAL_ERROR"
    else:
        code = "INTERNAL_ERROR"

    safe_message = re.sub(r"https?://\S+", "[tautan]", message)
    logger.warning("yt-dlp gagal (%s): %s", code, safe_message)
    return AppError(code)


def _mp4_selector(quality: str, *, with_ffmpeg: bool) -> str:
    if not with_ffmpeg:
        if quality == "best":
            return "b[ext=mp4]/b"
        return (
            f"b[height<={quality}][ext=mp4]/"
            f"b[height<={quality}]/b"
        )

    if quality == "best":
        return "bv*+ba/b"
    return (
        f"bv*[height<={quality}][ext=mp4][vcodec^=avc1]+ba[ext=m4a]/"
        f"bv*[height<={quality}][ext=mp4]+ba[ext=m4a]/"
        f"bv*[height<={quality}]+ba/"
        f"b[height<={quality}][ext=mp4]/"
        f"b[height<={quality}]/b"
    )


def _download_sync(
    target: ValidatedVideoURL,
    media_format: str,
    quality: str,
    job_dir: Path,
    cancel_event: threading.Event,
    timeout_seconds: int,
) -> tuple[Path, str]:
    deadline = time.monotonic() + timeout_seconds
    with_ffmpeg = ffmpeg_available()

    def progress_hook(_status: dict) -> None:
        if cancel_event.is_set() or time.monotonic() > deadline:
            raise DownloadCancelled("Batas waktu unduh tercapai")

    options = _base_options(job_dir)
    options["progress_hooks"] = [progress_hook]
    options["match_filter"] = match_filter_func(
        f"duration <= {settings.max_duration_seconds}"
    )

    if media_format == "mp3":
        options.update(
            {
                "format": "bestaudio/best",
                "postprocessors": [
                    {
                        "key": "FFmpegExtractAudio",
                        "preferredcodec": "mp3",
                        "preferredquality": "192",
                    }
                ],
            }
        )
    else:
        options["format"] = _mp4_selector(quality, with_ffmpeg=with_ffmpeg)
        if with_ffmpeg:
            options["merge_output_format"] = "mp4"

    try:
        with yt_dlp.YoutubeDL(options) as ydl:
            info = ydl.extract_info(target.url, download=True)
            if cancel_event.is_set() or time.monotonic() > deadline:
                raise DownloadCancelled("Batas waktu unduh tercapai")
    except DownloadCancelled as exc:
        raise AppError("TIMEOUT") from exc
    except DownloadError as exc:
        message = str(exc).lower()
        if "batas waktu" in message:
            raise AppError("TIMEOUT") from exc
        if not with_ffmpeg and "requested format is not available" in message:
            logger.warning(
                "Format progresif tidak tersedia tanpa ffmpeg; "
                "penggabungan video membutuhkan ffmpeg."
            )
            raise AppError("FFMPEG_MISSING") from exc
        raise _map_download_error(exc) from exc
    except AppError:
        raise
    except Exception as exc:  # noqa: BLE001
        logger.exception("Kesalahan tak terduga saat mengunduh.")
        raise AppError("INTERNAL_ERROR") from exc

    if not info:
        raise AppError("UNAVAILABLE")

    if info.get("_type") in {"playlist", "multi_video"}:
        entries = [entry for entry in (info.get("entries") or []) if entry]
        info = entries[0] if entries else {}

    if media_format == "mp3":
        path = pick_media_file(job_dir, "mp3")
        if path is None:
            raise AppError(
                "FFMPEG_MISSING" if not with_ffmpeg else "INTERNAL_ERROR"
            )
    else:
        path = pick_media_file(job_dir, "mp4")
        if path is None:
            fallback = find_media_file(job_dir)
            if fallback is None:
                raise AppError("INTERNAL_ERROR")
            if fallback.suffix.lower() != ".mp4":
                raise AppError(
                    "FFMPEG_MISSING" if not with_ffmpeg else "INTERNAL_ERROR"
                )
            path = fallback

    title = _clean_text(info.get("title"), 160, "video")
    return path, title


async def download_media(
    target: ValidatedVideoURL,
    media_format: MediaFormat,
    quality: Quality,
) -> DownloadResult:
    if media_format == "mp3" and not ffmpeg_available():
        raise AppError("FFMPEG_MISSING")

    async with _download_slots:
        try:
            job_dir = create_job_dir(settings.temp_dir)
        except OSError as exc:
            logger.exception("Tidak bisa membuat folder sementara.")
            raise AppError("INTERNAL_ERROR") from exc
        cancel_event = threading.Event()

        try:
            path, title = await asyncio.wait_for(
                run_in_threadpool(
                    _download_sync,
                    target,
                    media_format,
                    quality,
                    job_dir,
                    cancel_event,
                    settings.download_timeout_seconds,
                ),
                timeout=settings.download_timeout_seconds + 20,
            )
        except asyncio.TimeoutError as exc:
            cancel_event.set()
            cleanup_job_dir(job_dir)
            asyncio.get_running_loop().call_later(10, cleanup_job_dir, job_dir)
            logger.warning(
                "Unduhan timeout platform=%s format=%s", target.platform, media_format
            )
            raise AppError("TIMEOUT") from exc
        except AppError as exc:
            cleanup_job_dir(job_dir)
            logger.warning(
                "Unduhan gagal platform=%s format=%s code=%s",
                target.platform,
                media_format,
                exc.code,
            )
            raise
        except Exception as exc:  # noqa: BLE001
            cleanup_job_dir(job_dir)
            logger.exception("Unduhan gagal tanpa terduga.")
            raise AppError("INTERNAL_ERROR") from exc

        size = file_size_bytes(path)
        if size <= 0:
            cleanup_job_dir(job_dir)
            raise AppError("INTERNAL_ERROR")
        if size > settings.max_filesize_bytes:
            cleanup_job_dir(job_dir)
            logger.warning(
                "Ukuran file melebihi batas platform=%s bytes=%s",
                target.platform,
                size,
            )
            raise AppError("TOO_LARGE")

        extension = path.suffix.lower().lstrip(".")
        if media_format == "mp3" and extension != "mp3":
            cleanup_job_dir(job_dir)
            raise AppError("INTERNAL_ERROR")
        if media_format == "mp4" and extension != "mp4":
            cleanup_job_dir(job_dir)
            raise AppError(
                "FFMPEG_MISSING" if not ffmpeg_available() else "INTERNAL_ERROR"
            )

        filename = f"{safe_filename(title)}.{extension}"
        return DownloadResult(
            path=path,
            filename=filename,
            media_type=MEDIA_TYPES.get(extension, "application/octet-stream"),
            job_dir=job_dir,
        )
