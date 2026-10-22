"""Model request dan response Pydantic."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict

Quality = Literal["best", "1080", "720", "480", "360"]


class StrictRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class InfoRequest(StrictRequest):
    url: str


class DownloadRequest(StrictRequest):
    url: str
    format: Literal["mp4", "mp3"]
    quality: Quality = "best"


class FormatOption(BaseModel):
    quality: str
    height: int


class InfoResponse(BaseModel):
    platform: Literal["youtube", "tiktok"]
    title: str
    uploader: str
    thumbnail: str
    duration: int
    formats: list[FormatOption]


class HealthResponse(BaseModel):
    status: Literal["ok"]


class ErrorDetail(BaseModel):
    code: str
    message: str


class ErrorResponse(BaseModel):
    error: ErrorDetail
