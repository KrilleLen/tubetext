from __future__ import annotations

import html
import re
import threading
import time
from dataclasses import dataclass
from typing import Any
from urllib.parse import parse_qs, urlparse

import httpx
import requests

from .config import Settings
from .models import LanguageTrack, TranscriptResponse, TranscriptSegment, VideoMetadata

VIDEO_ID_RE = re.compile(r"^[A-Za-z0-9_-]{11}$")
ALLOWED_HOSTS = {
    "youtube.com",
    "www.youtube.com",
    "m.youtube.com",
    "music.youtube.com",
    "youtu.be",
    "www.youtu.be",
}


class TranscriptServiceError(RuntimeError):
    def __init__(self, message: str, code: str = "transcript_error", status_code: int = 400) -> None:
        super().__init__(message)
        self.code = code
        self.status_code = status_code


@dataclass
class _CacheEntry:
    expires_at: float
    value: dict[str, Any]


class TranscriptService:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self._cache: dict[str, _CacheEntry] = {}
        self._cache_lock = threading.Lock()

    @staticmethod
    def parse_video_id(value: str) -> str:
        raw = value.strip()
        if VIDEO_ID_RE.fullmatch(raw):
            return raw

        if not raw.lower().startswith(("http://", "https://")):
            raw = f"https://{raw}"

        parsed = urlparse(raw)
        host = (parsed.hostname or "").lower()
        if host not in ALLOWED_HOSTS:
            raise TranscriptServiceError(
                "Länken måste komma från youtube.com eller youtu.be.",
                code="invalid_url",
            )

        candidate: str | None = None
        path_parts = [part for part in parsed.path.split("/") if part]

        if host in {"youtu.be", "www.youtu.be"}:
            candidate = path_parts[0] if path_parts else None
        elif parsed.path == "/watch":
            candidate = parse_qs(parsed.query).get("v", [None])[0]
        elif path_parts and path_parts[0] in {"shorts", "embed", "live"}:
            candidate = path_parts[1] if len(path_parts) > 1 else None

        if candidate:
            candidate = candidate.split("?")[0].split("&")[0]

        if not candidate or not VIDEO_ID_RE.fullmatch(candidate):
            raise TranscriptServiceError(
                "Jag kunde inte hitta ett giltigt YouTube-video-ID i länken.",
                code="invalid_video_id",
            )
        return candidate

    def fetch(
        self,
        *,
        url: str,
        preferred_languages: list[str],
        language_code: str | None = None,
        translate_to: str | None = None,
    ) -> TranscriptResponse:
        video_id = self.parse_video_id(url)
        cache_key = "|".join(
            [video_id, language_code or "auto", ",".join(preferred_languages), translate_to or "none"]
        )
        cached = self._cache_get(cache_key)
        if cached is not None:
            cached["cached"] = True
            return TranscriptResponse.model_validate(cached)

        try:
            from youtube_transcript_api import YouTubeTranscriptApi
        except ImportError as exc:
            raise TranscriptServiceError(
                "Servern saknar paketet youtube-transcript-api. Installera projektets requirements.txt.",
                code="server_misconfigured",
                status_code=500,
            ) from exc

        session = requests.Session()
        session.headers.update(
            {
                "User-Agent": (
                    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124 Safari/537.36"
                )
            }
        )
        if self.settings.proxy_url:
            session.proxies.update({"http": self.settings.proxy_url, "https": self.settings.proxy_url})

        try:
            api = YouTubeTranscriptApi(http_client=session)
            transcript_list = api.list(video_id)
            tracks = list(transcript_list)
            if not tracks:
                raise TranscriptServiceError(
                    "Videon har ingen tillgänglig textning.",
                    code="no_transcript",
                )

            selected = self._select_track(
                tracks,
                language_code=language_code,
                preferred_languages=preferred_languages,
            )

            translated_to: str | None = None
            if translate_to and translate_to != selected.language_code:
                if not selected.is_translatable:
                    raise TranscriptServiceError(
                        "Den valda textningen kan inte översättas av YouTube.",
                        code="translation_unavailable",
                    )
                selected = selected.translate(translate_to)
                translated_to = translate_to

            fetched = selected.fetch(preserve_formatting=False)
            segments = [
                TranscriptSegment(
                    text=self._clean_text(item.text),
                    start=round(float(item.start), 3),
                    duration=round(float(item.duration), 3),
                )
                for item in fetched
                if getattr(item, "text", "").strip()
            ]
            if not segments:
                raise TranscriptServiceError(
                    "Textningen hittades men innehöll ingen text.",
                    code="empty_transcript",
                )

            metadata = self._get_metadata(video_id)
            response = TranscriptResponse(
                video=metadata,
                language=getattr(selected, "language", selected.language_code),
                language_code=selected.language_code,
                is_generated=bool(selected.is_generated),
                translated_to=translated_to,
                segments=segments,
                text=" ".join(segment.text for segment in segments),
                available_languages=[
                    LanguageTrack(
                        language=track.language,
                        language_code=track.language_code,
                        is_generated=bool(track.is_generated),
                        is_translatable=bool(track.is_translatable),
                    )
                    for track in tracks
                ],
                cached=False,
            )
            self._cache_set(cache_key, response.model_dump())
            return response
        except TranscriptServiceError:
            raise
        except Exception as exc:
            raise self._map_library_error(exc) from exc
        finally:
            session.close()

    @staticmethod
    def _select_track(
        tracks: list[Any],
        *,
        language_code: str | None,
        preferred_languages: list[str],
    ) -> Any:
        if language_code:
            exact = [track for track in tracks if track.language_code.lower() == language_code.lower()]
            if exact:
                return sorted(exact, key=lambda track: bool(track.is_generated))[0]
            raise TranscriptServiceError(
                f"Språket '{language_code}' finns inte för videon.",
                code="language_unavailable",
            )

        for preferred in preferred_languages:
            matches = [
                track
                for track in tracks
                if track.language_code.lower() == preferred.lower()
                or track.language_code.lower().startswith(f"{preferred.lower()}-")
            ]
            if matches:
                return sorted(matches, key=lambda track: bool(track.is_generated))[0]

        manual = [track for track in tracks if not track.is_generated]
        return manual[0] if manual else tracks[0]

    @staticmethod
    def _clean_text(value: str) -> str:
        text = html.unescape(value)
        text = re.sub(r"<[^>]+>", "", text)
        return re.sub(r"\s+", " ", text).strip()

    def _get_metadata(self, video_id: str) -> VideoMetadata:
        watch_url = f"https://www.youtube.com/watch?v={video_id}"
        title: str | None = None
        author_name: str | None = None

        try:
            with httpx.Client(timeout=self.settings.request_timeout_seconds, follow_redirects=False) as client:
                response = client.get(
                    "https://www.youtube.com/oembed",
                    params={"url": watch_url, "format": "json"},
                )
                if response.status_code == 200:
                    data = response.json()
                    title = str(data.get("title") or "").strip() or None
                    author_name = str(data.get("author_name") or "").strip() or None
        except (httpx.HTTPError, ValueError):
            pass

        return VideoMetadata(
            video_id=video_id,
            title=title,
            author_name=author_name,
            thumbnail_url=f"https://i.ytimg.com/vi/{video_id}/hqdefault.jpg",
            watch_url=watch_url,
            embed_url=f"https://www.youtube-nocookie.com/embed/{video_id}",
        )

    @staticmethod
    def _map_library_error(exc: Exception) -> TranscriptServiceError:
        name = exc.__class__.__name__
        message_map: dict[str, tuple[str, str, int]] = {
            "TranscriptsDisabled": ("Videons ägare har stängt av textning.", "transcripts_disabled", 404),
            "NoTranscriptFound": ("Ingen textning hittades på de valda språken.", "no_transcript", 404),
            "VideoUnavailable": ("Videon är privat, borttagen eller inte tillgänglig.", "video_unavailable", 404),
            "RequestBlocked": (
                "YouTube blockerade serverns förfrågan. Lägg till en roterande proxy för stabil molndrift.",
                "youtube_blocked",
                503,
            ),
            "IpBlocked": (
                "YouTube har blockerat serverns IP-adress. Lägg till YOUTUBE_PROXY_URL.",
                "youtube_ip_blocked",
                503,
            ),
            "AgeRestricted": ("Videon är åldersbegränsad och kan inte läsas utan inloggning.", "age_restricted", 403),
            "InvalidVideoId": ("Video-ID:t är ogiltigt.", "invalid_video_id", 400),
        }
        if name in message_map:
            message, code, status = message_map[name]
            return TranscriptServiceError(message, code=code, status_code=status)

        return TranscriptServiceError(
            "Det gick inte att hämta textningen från YouTube just nu.",
            code="provider_error",
            status_code=502,
        )

    def _cache_get(self, key: str) -> dict[str, Any] | None:
        now = time.monotonic()
        with self._cache_lock:
            entry = self._cache.get(key)
            if not entry:
                return None
            if entry.expires_at <= now:
                self._cache.pop(key, None)
                return None
            return dict(entry.value)

    def _cache_set(self, key: str, value: dict[str, Any]) -> None:
        with self._cache_lock:
            if len(self._cache) >= self.settings.cache_max_items:
                oldest_key = min(self._cache, key=lambda item: self._cache[item].expires_at)
                self._cache.pop(oldest_key, None)
            self._cache[key] = _CacheEntry(
                expires_at=time.monotonic() + self.settings.cache_ttl_seconds,
                value=dict(value),
            )
