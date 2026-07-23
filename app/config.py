from __future__ import annotations

import os
from dataclasses import dataclass
from urllib.parse import urlparse


def _as_bool(value: str | None, default: bool = False) -> bool:
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _csv(value: str | None, default: str = "") -> tuple[str, ...]:
    raw = value if value is not None else default
    return tuple(item.strip().rstrip("/") for item in raw.split(",") if item.strip())


def _valid_origins(values: tuple[str, ...]) -> tuple[str, ...]:
    origins: list[str] = []
    for value in values:
        if value == "*":
            origins.append(value)
            continue
        parsed = urlparse(value)
        if parsed.scheme in {"http", "https"} and parsed.netloc and not parsed.path.strip("/"):
            origins.append(value)
    return tuple(dict.fromkeys(origins))


@dataclass(frozen=True)
class Settings:
    app_name: str = os.getenv("APP_NAME", "TubeText")
    environment: str = os.getenv("ENVIRONMENT", "development")
    allowed_origins: tuple[str, ...] = _valid_origins(
        _csv(os.getenv("ALLOWED_ORIGINS"), "http://localhost:8000")
    )
    embed_allowed_origins: tuple[str, ...] = _valid_origins(
        _csv(os.getenv("EMBED_ALLOWED_ORIGINS"), "http://localhost:8000")
    )
    proxy_url: str | None = os.getenv("YOUTUBE_PROXY_URL") or None
    webshare_proxy_username: str | None = os.getenv("WEBSHARE_PROXY_USERNAME") or None
    webshare_proxy_password: str | None = os.getenv("WEBSHARE_PROXY_PASSWORD") or None
    webshare_proxy_countries: tuple[str, ...] = _csv(os.getenv("WEBSHARE_PROXY_COUNTRIES"), "se,de")
    request_timeout_seconds: float = float(os.getenv("REQUEST_TIMEOUT_SECONDS", "12"))
    cache_ttl_seconds: int = int(os.getenv("CACHE_TTL_SECONDS", "1800"))
    cache_max_items: int = int(os.getenv("CACHE_MAX_ITEMS", "200"))
    rate_limit_requests: int = int(os.getenv("RATE_LIMIT_REQUESTS", "20"))
    rate_limit_window_seconds: int = int(os.getenv("RATE_LIMIT_WINDOW_SECONDS", "60"))
    docs_enabled: bool = _as_bool(os.getenv("DOCS_ENABLED"), default=True)

    @property
    def proxy_mode(self) -> str:
        if self.webshare_proxy_username and self.webshare_proxy_password:
            return "webshare"
        if self.proxy_url:
            return "generic"
        return "none"

    @property
    def frame_ancestors(self) -> str:
        if not self.embed_allowed_origins:
            return "'none'"
        if "*" in self.embed_allowed_origins:
            return "*"
        return " ".join(("'self'", *self.embed_allowed_origins))

    @property
    def external_embedding_enabled(self) -> bool:
        return bool(self.embed_allowed_origins and self.embed_allowed_origins != ("http://localhost:8000",))


settings = Settings()
