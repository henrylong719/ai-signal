import pytest

from app.core.config import Settings


def _settings_kwargs() -> dict[str, object]:
    return {
        "PROJECT_NAME": "AI Signal Test",
        "FIRST_SUPERUSER": "admin@example.com",
        "FIRST_SUPERUSER_PASSWORD": "not-the-default-password",
        "DATABASE_URL": "postgresql://postgres:secret@localhost:5432/app",
    }


def _clear_settings_env(monkeypatch: pytest.MonkeyPatch) -> None:
    for name in [
        "SECRET_KEY",
        "PROJECT_NAME",
        "FIRST_SUPERUSER",
        "FIRST_SUPERUSER_PASSWORD",
        "DATABASE_URL",
        "ENVIRONMENT",
    ]:
        monkeypatch.delenv(name, raising=False)


def test_production_requires_explicit_secret_key(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _clear_settings_env(monkeypatch)

    with pytest.raises(ValueError, match="SECRET_KEY"):
        Settings(_env_file=None, ENVIRONMENT="production", **_settings_kwargs())


def test_production_accepts_explicit_secret_key(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _clear_settings_env(monkeypatch)

    settings = Settings(
        _env_file=None,
        ENVIRONMENT="production",
        SECRET_KEY="stable-production-secret",
        **_settings_kwargs(),
    )

    assert settings.SECRET_KEY == "stable-production-secret"
