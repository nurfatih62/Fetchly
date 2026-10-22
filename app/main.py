"""Entry point aplikasi FastAPI."""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse, PlainTextResponse
from starlette.exceptions import HTTPException as StarletteHTTPException
from starlette.middleware.trustedhost import TrustedHostMiddleware
from starlette.staticfiles import StaticFiles

from app.config import settings
from app.errors import AppError, message_for
from app.routes import router
from app.utils.files import cleanup_old_temp_dirs

logger = logging.getLogger("fetchly")

CSP = (
    "default-src 'self'; "
    "base-uri 'none'; "
    "object-src 'none'; "
    "frame-ancestors 'none'; "
    "form-action 'self'; "
    "script-src 'self'; "
    "style-src 'self'; "
    "img-src 'self' https:; "
    "media-src 'self' blob:; "
    "connect-src 'self'; "
    "font-src 'self'; "
    "worker-src 'none'"
)


@asynccontextmanager
async def lifespan(_app: FastAPI):
    try:
        settings.temp_dir.mkdir(parents=True, exist_ok=True)
        removed = cleanup_old_temp_dirs(settings.temp_dir)
        if removed:
            logger.info("Menghapus %s folder sementara yang sudah lama.", removed)
    except OSError:
        logger.exception("Tidak bisa menyiapkan folder sementara.")
    yield


app = FastAPI(
    title="Fetchly",
    version="1.0.0",
    docs_url=None,
    redoc_url=None,
    openapi_url=None,
    lifespan=lifespan,
)

app.add_middleware(
    TrustedHostMiddleware,
    allowed_hosts=["127.0.0.1", "localhost"],
)


@app.middleware("http")
async def add_security_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["Content-Security-Policy"] = CSP
    response.headers["Referrer-Policy"] = "no-referrer"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Permissions-Policy"] = (
        "camera=(), microphone=(), geolocation=(), payment=()"
    )
    if request.url.path.startswith("/api/"):
        response.headers.setdefault("Cache-Control", "no-store")
    return response


@app.exception_handler(AppError)
async def handle_app_error(_request: Request, exc: AppError) -> JSONResponse:
    return JSONResponse(
        status_code=exc.status_code,
        content=exc.to_dict(),
        headers={"Cache-Control": "no-store"},
    )


@app.exception_handler(RequestValidationError)
async def handle_validation_error(
    _request: Request, _exc: RequestValidationError
) -> JSONResponse:
    error = AppError("INVALID_REQUEST")
    return JSONResponse(
        status_code=error.status_code,
        content=error.to_dict(),
        headers={"Cache-Control": "no-store"},
    )


@app.exception_handler(StarletteHTTPException)
async def handle_http_error(
    request: Request, exc: StarletteHTTPException
) -> JSONResponse | PlainTextResponse:
    if request.url.path.startswith("/api/"):
        code = "METHOD_NOT_ALLOWED" if exc.status_code == 405 else "NOT_FOUND"
        if exc.status_code >= 500:
            code = "INTERNAL_ERROR"
        error = AppError(code)
        return JSONResponse(
            status_code=exc.status_code,
            content=error.to_dict(),
            headers={"Cache-Control": "no-store"},
        )
    return PlainTextResponse(
        "Halaman tidak ditemukan." if exc.status_code == 404 else "Terjadi kesalahan.",
        status_code=exc.status_code,
    )


@app.exception_handler(Exception)
async def handle_unexpected_error(
    request: Request, exc: Exception
) -> JSONResponse | PlainTextResponse:
    logger.exception("Kesalahan tak terduga pada %s.", request.url.path)
    if request.url.path.startswith("/api/"):
        error = AppError("INTERNAL_ERROR")
        return JSONResponse(
            status_code=500,
            content=error.to_dict(),
            headers={"Cache-Control": "no-store"},
        )
    return PlainTextResponse(
        message_for("INTERNAL_ERROR"),
        status_code=500,
    )


app.include_router(router)

_static_dir = Path(settings.static_dir)
app.mount("/", StaticFiles(directory=_static_dir, html=True), name="static")
