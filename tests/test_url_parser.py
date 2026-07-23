import pytest

from app.transcript_service import TranscriptService, TranscriptServiceError


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        ("dQw4w9WgXcQ", "dQw4w9WgXcQ"),
        ("https://www.youtube.com/watch?v=dQw4w9WgXcQ", "dQw4w9WgXcQ"),
        ("https://youtu.be/dQw4w9WgXcQ?t=12", "dQw4w9WgXcQ"),
        ("https://youtube.com/shorts/dQw4w9WgXcQ", "dQw4w9WgXcQ"),
        ("https://www.youtube.com/embed/dQw4w9WgXcQ", "dQw4w9WgXcQ"),
        ("music.youtube.com/watch?v=dQw4w9WgXcQ", "dQw4w9WgXcQ"),
    ],
)
def test_parse_video_id(value: str, expected: str) -> None:
    assert TranscriptService.parse_video_id(value) == expected


@pytest.mark.parametrize(
    "value",
    [
        "https://example.com/watch?v=dQw4w9WgXcQ",
        "https://youtube.com.evil.test/watch?v=dQw4w9WgXcQ",
        "not-video",
        "https://www.youtube.com/watch?v=too-short",
    ],
)
def test_parse_video_id_rejects_invalid_values(value: str) -> None:
    with pytest.raises(TranscriptServiceError):
        TranscriptService.parse_video_id(value)
