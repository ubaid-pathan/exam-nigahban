import pytest
from pydantic import ValidationError

from app.core.config import (
    INSECURE_SECRET_KEY_PLACEHOLDER,
    MIN_SECRET_KEY_LENGTH,
    Settings,
)

_VALID_SECRET_KEY = "a" * MIN_SECRET_KEY_LENGTH


def _build_settings(**overrides):
    """Build isolated Settings for testing SECRET_KEY validation."""
    return Settings(
        secret_key=overrides.pop("secret_key", _VALID_SECRET_KEY),
        **overrides,
    )


def test_secret_key_missing_is_rejected(monkeypatch):
    """SECRET_KEY must be explicitly configured."""
    monkeypatch.delenv("SECRET_KEY", raising=False)

    # Disable the .env source so the test verifies that the
    # required SECRET_KEY field has no fallback default.
    with pytest.raises(ValidationError) as exc_info:
        Settings(_env_file=None)  # type: ignore[call-arg]

    assert "secret_key" in str(exc_info.value).lower()


def test_secret_key_placeholder_is_rejected():
    """The known insecure placeholder must never be accepted."""
    with pytest.raises(ValidationError) as exc_info:
        _build_settings(
            secret_key=INSECURE_SECRET_KEY_PLACEHOLDER
        )

    assert "placeholder" in str(exc_info.value).lower()


def test_secret_key_empty_string_is_rejected():
    """An empty SECRET_KEY must be rejected."""
    with pytest.raises(ValidationError) as exc_info:
        _build_settings(secret_key="")

    assert "empty" in str(exc_info.value).lower()


def test_secret_key_too_short_is_rejected():
    """SECRET_KEY values shorter than the minimum must be rejected."""
    with pytest.raises(ValidationError) as exc_info:
        _build_settings(
            secret_key="a" * (MIN_SECRET_KEY_LENGTH - 1)
        )

    assert str(MIN_SECRET_KEY_LENGTH) in str(exc_info.value)


def test_secret_key_at_minimum_length_is_accepted():
    """A SECRET_KEY at the minimum allowed length is accepted."""
    secret = "a" * MIN_SECRET_KEY_LENGTH

    settings = _build_settings(secret_key=secret)

    assert settings.secret_key == secret


def test_secret_key_valid_value_is_accepted():
    """A sufficiently long configured SECRET_KEY is accepted."""
    secret = "a-sufficiently-long-valid-secret-value-123"

    settings = _build_settings(secret_key=secret)

    assert settings.secret_key == secret


def test_running_app_settings_pass_validation():
    """
    Verify that the module-level Settings singleton used by the
    running application contains a valid SECRET_KEY.
    """
    from app.core.config import settings

    assert settings.secret_key != INSECURE_SECRET_KEY_PLACEHOLDER
    assert len(settings.secret_key) >= MIN_SECRET_KEY_LENGTH