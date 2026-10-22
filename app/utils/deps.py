"""Pemeriksaan dependensi: ffmpeg dan yt-dlp."""

from __future__ import annotations

import importlib.metadata
import platform
import shutil

FFMPEG_HELP = """\
ffmpeg belum terpasang. Aplikasi tetap bisa dibuka, tetapi unduhan MP3
dan penggabungan video MP4 membutuhkan ffmpeg.

Cara memasang di Windows:
  1. Buka PowerShell atau Terminal.
  2. Jalankan: winget install Gyan.FFmpeg
  3. Tutup lalu buka kembali terminal, kemudian jalankan ulang aplikasi.
  4. Cek dengan: ffmpeg -version

Alternatif manual: https://www.gyan.dev/ffmpeg/builds/
"""


def ffmpeg_available() -> bool:
    """True jika ffmpeg dapat ditemukan di PATH."""
    return shutil.which("ffmpeg") is not None


def ytdlp_version() -> str:
    try:
        return importlib.metadata.version("yt-dlp")
    except importlib.metadata.PackageNotFoundError:
        return "tidak terpasang"


def python_version() -> str:
    return platform.python_version()


def dependency_status() -> dict[str, object]:
    return {
        "ffmpeg": ffmpeg_available(),
        "ytdlp_version": ytdlp_version(),
    }
