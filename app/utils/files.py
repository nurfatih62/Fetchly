"""Pembersihan folder sementara dan pembuatan nama file yang aman."""

from __future__ import annotations

import re
import shutil
import time
import unicodedata
import uuid
from pathlib import Path

_INVALID_FILENAME_CHARS = re.compile(r'[<>:"/\\|?*\x00-\x1f\x7f]')
_WINDOWS_RESERVED_NAMES = {
    "CON",
    "PRN",
    "AUX",
    "NUL",
    *(f"COM{index}" for index in range(1, 10)),
    *(f"LPT{index}" for index in range(1, 10)),
}
MEDIA_EXTENSIONS = {"mp4", "mp3", "webm", "mkv", "m4a", "mov"}


def safe_filename(value: str | None, *, fallback: str = "video", max_length: int = 120) -> str:
    """Ubah judul video menjadi nama file aman untuk Windows dan browser."""
    name = unicodedata.normalize("NFKC", str(value or ""))
    name = _INVALID_FILENAME_CHARS.sub(" ", name)
    name = re.sub(r"\s+", " ", name).strip(" .")

    if not name:
        name = fallback

    stem = name.split(".", 1)[0].strip().upper()
    if stem in _WINDOWS_RESERVED_NAMES:
        name = f"video-{name}"

    if len(name) > max_length:
        name = name[:max_length].rstrip(" .")

    return name or fallback


def create_job_dir(temp_dir: Path) -> Path:
    temp_dir.mkdir(parents=True, exist_ok=True)
    job_dir = temp_dir / uuid.uuid4().hex
    job_dir.mkdir(parents=True, exist_ok=False)
    return job_dir


def cleanup_job_dir(job_dir: Path | None) -> None:
    if job_dir is None:
        return
    shutil.rmtree(job_dir, ignore_errors=True)


def cleanup_old_temp_dirs(temp_dir: Path, max_age_seconds: int = 30 * 60) -> int:
    """Hapus folder job yang lebih tua dari batas usia. Kembalikan jumlahnya."""
    if not temp_dir.exists():
        return 0

    cutoff = time.time() - max_age_seconds
    removed = 0
    try:
        entries = list(temp_dir.iterdir())
    except OSError:
        return 0

    for entry in entries:
        try:
            if not entry.is_dir() or entry.is_symlink():
                continue
            if entry.stat().st_mtime >= cutoff:
                continue
            shutil.rmtree(entry, ignore_errors=True)
            if not entry.exists():
                removed += 1
        except OSError:
            continue
    return removed


def pick_media_file(job_dir: Path, extension: str) -> Path | None:
    """Pilih file hasil unduhan dengan ekstensi tertentu."""
    wanted = "." + extension.lower().lstrip(".")
    candidates: list[Path] = []
    try:
        for entry in job_dir.iterdir():
            if not entry.is_file():
                continue
            if entry.suffix.lower() != wanted:
                continue
            if entry.name.endswith((".part", ".ytdl")):
                continue
            candidates.append(entry)
    except OSError:
        return None

    if not candidates:
        return None

    try:
        return max(candidates, key=lambda item: item.stat().st_mtime)
    except OSError:
        return candidates[0]


def find_media_file(job_dir: Path) -> Path | None:
    """Cari file media apa pun di folder job, terbaru lebih dulu."""
    candidates: list[Path] = []
    try:
        for entry in job_dir.iterdir():
            if not entry.is_file():
                continue
            if entry.suffix.lower().lstrip(".") not in MEDIA_EXTENSIONS:
                continue
            if entry.name.endswith((".part", ".ytdl")):
                continue
            candidates.append(entry)
    except OSError:
        return None

    if not candidates:
        return None

    try:
        return max(candidates, key=lambda item: item.stat().st_mtime)
    except OSError:
        return candidates[0]


def file_size_bytes(path: Path) -> int:
    try:
        return path.stat().st_size
    except OSError:
        return 0
