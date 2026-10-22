"""Konfigurasi aplikasi.

Semua nilai bersifat opsional dan dapat diubah lewat file ``.env`` atau
environment variable. Nilai bawaan sudah aman untuk pemakaian biasa.
"""

from __future__ import annotations

import logging
import os
import tempfile
from dataclasses import dataclass
from pathlib import Path

try:
    from dotenv import load_dotenv
except ImportError:  # pragma: no cover - fallback agar aplikasi tetap bisa dibuka
    def load_dotenv(*_args, **_kwargs):
        return False


BASE_DIR = Path(__file__).resolve().parent.parent
ENV_FILE = BASE_DIR / ".env"

load_dotenv(ENV_FILE)

logger = logging.getLogger(__name__)


def _read_int(
    name: str,
    default: int,
    *,
    minimum: int = 1,
    maximum: int | None = None,
) -> int:
    raw = os.getenv(name)
    if raw is None or not raw.strip():
        return default

    try:
        value = int(raw.strip())
    except ValueError:
        logger.warning("Nilai %s tidak valid. Memakai bawaan %s.", name, default)
        return default

    if value < minimum:
        logger.warning(
            "Nilai %s terlalu kecil. Memakai batas minimum %s.", name, minimum
        )
        return minimum
    if maximum is not None and value > maximum:
        logger.warning(
            "Nilai %s terlalu besar. Memakai batas maksimum %s.", name, maximum
        )
        return maximum
    return value


def _read_temp_dir() -> Path:
    raw = os.getenv("TEMP_DIR", "").strip()
    if not raw:
        return Path(tempfile.gettempdir()) / "vdl"

    path = Path(raw).expanduser()
    if not path.is_absolute():
        path = (BASE_DIR / path).resolve()
    return path


@dataclass(frozen=True)
class Settings:
    base_dir: Path
    static_dir: Path
    landing_dir: Path
    temp_dir: Path
    max_duration_seconds: int
    max_filesize_mb: int
    max_parallel_jobs: int
    download_timeout_seconds: int
    port: int
    host: str = "127.0.0.1"
    info_timeout_seconds: int = 45

    @property
    def max_filesize_bytes(self) -> int:
        return self.max_filesize_mb * 1024 * 1024


settings = Settings(
    base_dir=BASE_DIR,
    static_dir=BASE_DIR / "static",
    landing_dir=BASE_DIR / "landing",
    temp_dir=_read_temp_dir(),
    max_duration_seconds=_read_int("MAX_DURATION_SECONDS", 900),
    max_filesize_mb=_read_int("MAX_FILESIZE_MB", 500),
    max_parallel_jobs=_read_int("MAX_PARALLEL_JOBS", 2, maximum=8),
    download_timeout_seconds=_read_int("DOWNLOAD_TIMEOUT_SECONDS", 180, minimum=10),
    port=_read_int("PORT", 8000, maximum=65535),
)
