from fastapi.testclient import TestClient

from app.main import app
from app.models import TranscriptResponse

client = TestClient(app)


def test_health() -> None:
    response = client.get("/api/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"
    assert response.json()["version"] == "1.1.0"


def test_index() -> None:
    response = client.get("/")
    assert response.status_code == 200
    assert "TubeText" in response.text
    assert "Content-Security-Policy" in response.headers
    assert "frame-ancestors" in response.headers["Content-Security-Policy"]


def test_embed_route() -> None:
    response = client.get("/embed")
    assert response.status_code == 200
    assert "TubeText" in response.text


def test_widget_asset() -> None:
    response = client.get("/static/widget.js")
    assert response.status_code == 200
    assert "tubetext-widget" in response.text
    assert response.headers["Cache-Control"].startswith("public")


def test_transcript_endpoint_with_stub(monkeypatch) -> None:
    payload = TranscriptResponse.model_validate(
        {
            "video": {
                "video_id": "dQw4w9WgXcQ",
                "title": "Testvideo",
                "author_name": "Testkanal",
                "thumbnail_url": "https://i.ytimg.com/vi/dQw4w9WgXcQ/hqdefault.jpg",
                "watch_url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
                "embed_url": "https://www.youtube-nocookie.com/embed/dQw4w9WgXcQ",
            },
            "language": "Swedish",
            "language_code": "sv",
            "is_generated": True,
            "segments": [{"text": "Hej världen", "start": 0.0, "duration": 1.2}],
            "text": "Hej världen",
            "available_languages": [
                {
                    "language": "Swedish",
                    "language_code": "sv",
                    "is_generated": True,
                    "is_translatable": True,
                }
            ],
        }
    )

    monkeypatch.setattr("app.main.service.fetch", lambda **_: payload)
    response = client.post(
        "/api/transcripts",
        json={"url": "https://youtu.be/dQw4w9WgXcQ", "preferred_languages": ["sv", "en"]},
    )
    assert response.status_code == 200
    assert response.json()["text"] == "Hej världen"
