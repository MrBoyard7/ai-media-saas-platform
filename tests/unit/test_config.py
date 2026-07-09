"""Unit tests for `app.core.config.Settings`.

`Settings(...)` accepts direct keyword overrides in addition to reading
from the environment/`.env`, which is what makes it practical to unit
test validation behavior without touching real env vars.
"""
from __future__ import annotations

from app.core.config import Settings


def test_blank_storage_bucket_url_is_treated_as_unset():
    """Regression test: `.env.example` ships `STORAGE_BUCKET_URL=` (blank)
    since object storage isn't configured out of the box. Pydantic's
    `AnyUrl` validator doesn't treat "" as None on its own and used to
    crash app startup with a ValidationError -- see the field_validator
    docstring in app/core/config.py for the fix."""
    settings = Settings(STORAGE_BUCKET_URL="")
    assert settings.STORAGE_BUCKET_URL is None


def test_whitespace_only_storage_bucket_url_is_treated_as_unset():
    settings = Settings(STORAGE_BUCKET_URL="   ")
    assert settings.STORAGE_BUCKET_URL is None


def test_real_storage_bucket_url_still_validates():
    settings = Settings(STORAGE_BUCKET_URL="https://storage.example.com/bucket")
    assert str(settings.STORAGE_BUCKET_URL) == "https://storage.example.com/bucket"


def test_unset_storage_bucket_url_defaults_to_none():
    settings = Settings()
    assert settings.STORAGE_BUCKET_URL is None
