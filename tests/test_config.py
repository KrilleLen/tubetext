from app.config import Settings


def test_frame_ancestors_are_restricted() -> None:
    configured = Settings(embed_allowed_origins=("https://example.com",))
    assert configured.frame_ancestors == "'self' https://example.com"
    assert configured.external_embedding_enabled is True


def test_no_embedding_is_deny_by_default_when_empty() -> None:
    configured = Settings(embed_allowed_origins=())
    assert configured.frame_ancestors == "'none'"
