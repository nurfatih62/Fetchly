"""Launcher Fetchly untuk Windows.

Memeriksa dependensi, menjalankan server hanya di 127.0.0.1, lalu membuka
browser secara otomatis.
"""

from __future__ import annotations

import logging
import socket
import sys
import threading
import webbrowser
from pathlib import Path

MIN_PYTHON = (3, 11)
BASE_DIR = Path(__file__).resolve().parent


def _port_is_free(host: str, port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        try:
            sock.bind((host, port))
        except OSError:
            return False
    return True


def _print_header() -> None:
    print()
    print("  Fetchly 1.0.0")
    print("  Pengunduh video lokal untuk YouTube dan TikTok")
    print("  " + "-" * 51)
    print()


def main() -> int:
    if sys.version_info < MIN_PYTHON:
        required = ".".join(str(part) for part in MIN_PYTHON)
        current = ".".join(str(part) for part in sys.version_info[:3])
        print(f"Python {required} atau lebih baru dibutuhkan. Versi saat ini: {current}.")
        print("Unduh Python terbaru dari https://www.python.org/downloads/")
        return 1

    try:
        from dotenv import load_dotenv

        load_dotenv(BASE_DIR / ".env")
    except ImportError:
        pass

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s  %(levelname)-7s %(name)s: %(message)s",
        datefmt="%H:%M:%S",
    )

    from app.config import settings
    from app.utils.deps import FFMPEG_HELP, ffmpeg_available, ytdlp_version

    _print_header()

    if ffmpeg_available():
        print("  ffmpeg       : ditemukan")
    else:
        print("  ffmpeg       : TIDAK DITEMUKAN")
        print()
        print(FFMPEG_HELP)

    ytdlp = ytdlp_version()
    print(f"  yt-dlp       : {ytdlp}")
    print(f"  folder temp  : {settings.temp_dir}")
    limit_minutes = f"{settings.max_duration_seconds / 60:g}"
    print(
        f"  batas        : {limit_minutes} menit, "
        f"{settings.max_filesize_mb} MB"
    )
    print()

    if ytdlp == "tidak terpasang":
        print("yt-dlp belum terpasang. Jalankan perintah berikut, lalu coba lagi:")
        print("  pip install -r requirements.txt")
        return 1

    if not _port_is_free(settings.host, settings.port):
        print(
            f"Port {settings.port} sudah dipakai aplikasi lain. "
            "Tutup aplikasi tersebut, atau ubah PORT di file .env."
        )
        print("Contoh di PowerShell:  $env:PORT=8001; python run.py")
        return 1

    url = f"http://{settings.host}:{settings.port}"
    print(f"  Aplikasi berjalan di {url}")
    print("  Hanya bisa diakses dari komputer ini.")
    print("  Tekan Ctrl+C untuk menghentikan.")
    print()

    try:
        import uvicorn
    except ImportError:
        print("uvicorn belum terpasang. Jalankan: pip install -r requirements.txt")
        return 1

    browser_timer = threading.Timer(1.5, webbrowser.open, args=(url,))
    browser_timer.daemon = True
    browser_timer.start()

    try:
        uvicorn.run(
            "app.main:app",
            host=settings.host,
            port=settings.port,
            log_level="info",
            access_log=False,
        )
    except KeyboardInterrupt:
        pass
    except Exception as exc:  # noqa: BLE001 - pesan ramah untuk pengguna
        print(f"\nServer gagal dijalankan: {exc}")
        return 1
    finally:
        browser_timer.cancel()

    print("\nAplikasi berhenti.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
