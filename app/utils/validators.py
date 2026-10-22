"""Validasi dan normalisasi tautan YouTube dan TikTok.

Whitelist host dicocokkan persis. Pengecekan tidak memakai ``endswith``
terhadap domain, sehingga domain seperti ``youtube.com.evil.net`` ditolak.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Literal
from urllib.parse import parse_qs, unquote, urlsplit

MAX_URL_LENGTH = 2048

YOUTUBE_HOSTS = frozenset(
    {
        "youtube.com",
        "www.youtube.com",
        "m.youtube.com",
        "youtu.be",
    }
)
TIKTOK_HOSTS = frozenset(
    {
        "tiktok.com",
        "www.tiktok.com",
        "vm.tiktok.com",
        "vt.tiktok.com",
    }
)
SHORT_TIKTOK_HOSTS = frozenset({"vm.tiktok.com", "vt.tiktok.com"})
ALLOWED_HOSTS = YOUTUBE_HOSTS | TIKTOK_HOSTS

# Hanya dipakai untuk memberi pesan "platform belum didukung", bukan untuk
# mengizinkan akses.
OTHER_PLATFORM_DOMAINS = (
    "vimeo.com",
    "instagram.com",
    "facebook.com",
    "fb.watch",
    "twitter.com",
    "x.com",
    "dailymotion.com",
    "twitch.tv",
    "spotify.com",
    "soundcloud.com",
    "reddit.com",
    "pinterest.com",
    "snapchat.com",
    "linkedin.com",
    "netflix.com",
    "bilibili.com",
)

_ALLOWED_BASE_DOMAINS = ("youtube.com", "youtu.be", "tiktok.com")

_YOUTUBE_ID_RE = re.compile(r"^[A-Za-z0-9_-]{11}$")
_TIKTOK_VIDEO_PATH_RE = re.compile(
    r"^/@([A-Za-z0-9._-]{1,64})/video/([0-9]{5,25})$"
)
_TIKTOK_SHORT_CODE_RE = re.compile(r"^[A-Za-z0-9]{4,32}$")

Platform = Literal["youtube", "tiktok"]


@dataclass(frozen=True, slots=True)
class ValidatedVideoURL:
    url: str
    platform: Platform
    video_id: str


class URLValidationError(ValueError):
    """Input bukan tautan video YouTube/TikTok yang didukung."""

    def __init__(self, code: str = "INVALID_URL") -> None:
        self.code = code
        super().__init__(code)


def _matches_domain(host: str, domain: str) -> bool:
    return host == domain or host.endswith("." + domain)


def _imitates_allowed_host(host: str) -> bool:
    """Deteksi domain palsu yang menyerupai host yang diizinkan."""
    for domain in _ALLOWED_BASE_DOMAINS:
        if host.startswith(domain + ".") or _matches_domain(host, domain):
            return True
    return False


def _reject(code: str = "INVALID_URL") -> None:
    raise URLValidationError(code)


def _validate_youtube(host: str, path: str, query: str) -> tuple[str, str]:
    normalized_path = unquote(path)

    if host == "youtu.be":
        segments = [segment for segment in normalized_path.split("/") if segment]
        if len(segments) != 1 or not _YOUTUBE_ID_RE.fullmatch(segments[0]):
            _reject()
        return segments[0], f"https://www.youtube.com/watch?v={segments[0]}"

    cleaned_path = normalized_path.rstrip("/") or "/"

    if cleaned_path == "/watch":
        values = parse_qs(query, keep_blank_values=True).get("v", [])
        if len(values) != 1 or not _YOUTUBE_ID_RE.fullmatch(values[0]):
            _reject()
        video_id = values[0]
        return video_id, f"https://www.youtube.com/watch?v={video_id}"

    segments = [segment for segment in cleaned_path.split("/") if segment]
    if len(segments) == 2 and segments[0] in {"shorts", "live", "embed"}:
        video_id = segments[1]
        if not _YOUTUBE_ID_RE.fullmatch(video_id):
            _reject()
        return video_id, f"https://www.youtube.com/watch?v={video_id}"

    _reject()


def _validate_tiktok(host: str, path: str) -> tuple[str, str]:
    normalized_path = unquote(path).rstrip("/") or "/"

    if host in SHORT_TIKTOK_HOSTS:
        segments = [segment for segment in normalized_path.split("/") if segment]
        if len(segments) != 1 or not _TIKTOK_SHORT_CODE_RE.fullmatch(segments[0]):
            _reject()
        code = segments[0]
        return code, f"https://{host}/{code}"

    match = _TIKTOK_VIDEO_PATH_RE.fullmatch(normalized_path)
    if not match:
        _reject()
    username, video_id = match.groups()
    return video_id, f"https://www.tiktok.com/@{username.lower()}/video/{video_id}"


def validate_video_url(raw_url: str) -> ValidatedVideoURL:
    """Validasi tautan dan kembalikan URL yang sudah dinormalisasi.

    Hanya skema http/https, host dari whitelist, dan bentuk tautan video
    tunggal yang diterima. Query pelacak dan fragmen dibuang.
    """

    if not isinstance(raw_url, str):
        _reject()

    url = raw_url.strip()
    if not url or len(url) > MAX_URL_LENGTH:
        _reject()
    if any(character.isspace() or ord(character) < 32 for character in url):
        _reject()

    try:
        parts = urlsplit(url)
        scheme = parts.scheme.lower()
        host = (parts.hostname or "").lower()
        port = parts.port
    except ValueError:
        _reject()

    if scheme not in {"http", "https"}:
        _reject()
    if not host:
        _reject()
    if parts.username is not None or parts.password is not None:
        _reject()
    if port is not None:
        _reject()

    if host not in ALLOWED_HOSTS:
        if _imitates_allowed_host(host):
            _reject("INVALID_URL")
        if any(_matches_domain(host, domain) for domain in OTHER_PLATFORM_DOMAINS):
            _reject("UNSUPPORTED_PLATFORM")
        _reject("INVALID_URL")

    if host in YOUTUBE_HOSTS:
        video_id, normalized = _validate_youtube(host, parts.path, parts.query)
        return ValidatedVideoURL(
            url=normalized, platform="youtube", video_id=video_id
        )

    video_id, normalized = _validate_tiktok(host, parts.path)
    return ValidatedVideoURL(url=normalized, platform="tiktok", video_id=video_id)
