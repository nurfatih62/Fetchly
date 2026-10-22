"""Kode error dan pesan Bahasa Indonesia untuk API."""

from __future__ import annotations

from app.config import settings


def _max_minutes() -> str:
    seconds = settings.max_duration_seconds
    if seconds % 60 == 0:
        return str(seconds // 60)
    return f"{seconds / 60:.1f}".rstrip("0").rstrip(".")


MESSAGES = {
    "INVALID_URL": "Link tidak valid. Tempel link video YouTube atau TikTok.",
    "UNSUPPORTED_PLATFORM": (
        "Platform ini belum didukung. Saat ini hanya YouTube dan TikTok."
    ),
    "UNAVAILABLE": (
        "Video tidak bisa diakses. Mungkin privat, dihapus, atau dibatasi di wilayahmu."
    ),
    "RESTRICTED": (
        "Video ini hanya untuk member atau pembeli, jadi tidak bisa diunduh."
    ),
    "TOO_LONG": "Durasi video melebihi {max} menit.",
    "TOO_LARGE": "Ukuran file melebihi {max} MB. Coba kualitas yang lebih rendah.",
    "TIMEOUT": "Proses terlalu lama. Coba lagi beberapa saat.",
    "FFMPEG_MISSING": "ffmpeg belum terpasang. Lihat panduan di README.",
    "INTERNAL_ERROR": (
        "Terjadi kesalahan. Coba lagi nanti. Jika terus terjadi, "
        "perbarui yt-dlp dengan `pip install -U yt-dlp`."
    ),
    "INVALID_REQUEST": "Permintaan tidak valid.",
    "NOT_FOUND": "Alamat yang diminta tidak ditemukan.",
    "METHOD_NOT_ALLOWED": "Metode permintaan tidak didukung.",
}


STATUS_CODES = {
    "INVALID_URL": 400,
    "UNSUPPORTED_PLATFORM": 400,
    "INVALID_REQUEST": 422,
    "UNAVAILABLE": 404,
    "RESTRICTED": 403,
    "TOO_LONG": 422,
    "TOO_LARGE": 413,
    "TIMEOUT": 504,
    "FFMPEG_MISSING": 503,
    "INTERNAL_ERROR": 500,
    "NOT_FOUND": 404,
    "METHOD_NOT_ALLOWED": 405,
}


def message_for(code: str) -> str:
    template = MESSAGES.get(code, MESSAGES["INTERNAL_ERROR"])
    return template.format(
        max=_max_minutes() if code == "TOO_LONG" else settings.max_filesize_mb
    )


class AppError(Exception):
    """Error yang aman ditampilkan ke pengguna."""

    def __init__(self, code: str, message: str | None = None) -> None:
        self.code = code if code in MESSAGES else "INTERNAL_ERROR"
        self.message = message or message_for(self.code)
        self.status_code = STATUS_CODES.get(self.code, 500)
        super().__init__(self.message)

    def to_dict(self) -> dict[str, dict[str, str]]:
        return {"error": {"code": self.code, "message": self.message}}
