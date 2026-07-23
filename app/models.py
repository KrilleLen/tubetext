from __future__ import annotations

from pydantic import BaseModel, Field, field_validator


class TranscriptRequest(BaseModel):
    url: str = Field(min_length=1, max_length=500)
    preferred_languages: list[str] = Field(default_factory=lambda: ["sv", "en"], max_length=10)
    language_code: str | None = Field(default=None, max_length=20)
    translate_to: str | None = Field(default=None, max_length=20)

    @field_validator("preferred_languages")
    @classmethod
    def clean_languages(cls, values: list[str]) -> list[str]:
        cleaned: list[str] = []
        for value in values:
            code = value.strip().lower()
            if code and code not in cleaned:
                cleaned.append(code)
        return cleaned[:10] or ["sv", "en"]

    @field_validator("language_code", "translate_to")
    @classmethod
    def clean_optional_language(cls, value: str | None) -> str | None:
        if value is None:
            return None
        value = value.strip().lower()
        return value or None


class TranscriptSegment(BaseModel):
    text: str
    start: float
    duration: float


class LanguageTrack(BaseModel):
    language: str
    language_code: str
    is_generated: bool
    is_translatable: bool


class VideoMetadata(BaseModel):
    video_id: str
    title: str | None = None
    author_name: str | None = None
    thumbnail_url: str
    watch_url: str
    embed_url: str


class TranscriptResponse(BaseModel):
    video: VideoMetadata
    language: str
    language_code: str
    is_generated: bool
    translated_to: str | None = None
    segments: list[TranscriptSegment]
    text: str
    available_languages: list[LanguageTrack]
    cached: bool = False


class ErrorResponse(BaseModel):
    error: str
    code: str
    detail: str | None = None
