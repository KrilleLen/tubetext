from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI, HTTPException, Request
from fastapi.concurrency import run_in_threadpool
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from .config import settings
from .models import ErrorResponse, TranscriptRequest, TranscriptResponse
from .rate_limit import InMemoryRateLimiter
from .transcript_service import TranscriptService, TranscriptServiceError

BASE_DIR = Path(__file__).resolve().parent
STATIC_DIR = BASE_DIR / "static"

app = FastAPI(
    title=settings.app_name,
    version="1.1.0",
    docs_url="/docs" if settings.docs_enabled else None,
    redoc_url=None,
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=list(settings.allowed_origins),
    allow_credentials=False,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["Content-Type", "Accept"],
)
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

service = TranscriptService(settings)
limiter = InMemoryRateLimiter(
    max_requests=settings.rate_limit_requests,
    window_seconds=settings.rate_limit_window_seconds,
)


@app.middleware("http")
async def security_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"

    # X-Frame-Options cannot express a list of external domains. When external
    # embedding is enabled, CSP frame-ancestors is the authoritative policy.
    if not settings.external_embedding_enabled:
        response.headers["X-Frame-Options"] = "SAMEORIGIN"

    response.headers["Content-Security-Policy"] = (
        "default-src 'self'; "
        "script-src 'self'; "
        "style-src 'self'; "
        "img-src 'self' data: https://i.ytimg.com; "
        "frame-src https://www.youtube-nocookie.com; "
        "connect-src 'self'; "
        "base-uri 'self'; form-action 'self'; "
        f"frame-ancestors {settings.frame_ancestors}"
    )

    if request.url.path.startswith("/static/"):
        response.headers["Cache-Control"] = "public, max-age=86400"
    else:
        response.headers.setdefault("Cache-Control", "no-store")
    return response


@app.get("/", include_in_schema=False)
@app.get("/embed", include_in_schema=False)
async def index() -> FileResponse:
    return FileResponse(STATIC_DIR / "index.html")


@app.get("/api/health")
@app.get("/healthz", include_in_schema=False)
async def health() -> dict[str, str]:
    return {"status": "ok", "service": settings.app_name, "version": app.version}


@app.post(
    "/api/transcripts",
    response_model=TranscriptResponse,
    responses={
        400: {"model": ErrorResponse},
        404: {"model": ErrorResponse},
        429: {"model": ErrorResponse},
        502: {"model": ErrorResponse},
        503: {"model": ErrorResponse},
    },
)
async def create_transcript(payload: TranscriptRequest, request: Request) -> TranscriptResponse:
    client_ip = request.client.host if request.client else "unknown"
    allowed, retry_after = limiter.allow(client_ip)
    if not allowed:
        raise HTTPException(
            status_code=429,
            detail={
                "error": "För många förfrågningar. Försök igen om en liten stund.",
                "code": "rate_limited",
                "retry_after": retry_after,
            },
            headers={"Retry-After": str(retry_after)},
        )

    try:
        return await run_in_threadpool(
            service.fetch,
            url=payload.url,
            preferred_languages=payload.preferred_languages,
            language_code=payload.language_code,
            translate_to=payload.translate_to,
        )
    except TranscriptServiceError as exc:
        return JSONResponse(
            status_code=exc.status_code,
            content={"error": str(exc), "code": exc.code},
        )


@app.exception_handler(HTTPException)
async def http_exception_handler(_: Request, exc: HTTPException) -> JSONResponse:
    if isinstance(exc.detail, dict):
        payload = exc.detail
    else:
        payload = {"error": str(exc.detail), "code": "http_error"}
    return JSONResponse(status_code=exc.status_code, content=payload, headers=exc.headers)
