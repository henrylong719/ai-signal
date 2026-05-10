import secrets
import warnings
from typing import Annotated, Any, Literal

from pydantic import (
    AnyUrl,
    BeforeValidator,
    EmailStr,
    HttpUrl,
    PostgresDsn,
    computed_field,
    model_validator,
)
from pydantic_settings import BaseSettings, SettingsConfigDict
from typing_extensions import Self


def parse_cors(v: Any) -> list[str] | str:
    if isinstance(v, str) and not v.startswith("["):
        return [i.strip() for i in v.split(",") if i.strip()]
    elif isinstance(v, list | str):
        return v
    raise ValueError(v)


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        # Use top level .env file (one level above ./backend/)
        env_file="../.env",
        env_ignore_empty=True,
        extra="ignore",
    )
    API_V1_STR: str = "/api/v1"
    SECRET_KEY: str = secrets.token_urlsafe(32)
    # 15-minute access token, refreshed via the refresh cookie. Pre-cookie-auth
    # this was 8 days (60 * 24 * 8) because there was no refresh path — losing
    # the token meant logging back in. With refresh tokens, the access token
    # only needs to live long enough that we're not refreshing on every
    # request. 15 minutes is the conventional sweet spot.
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 15
    REFRESH_TOKEN_EXPIRE_DAYS: int = 30
    FRONTEND_HOST: str = "http://localhost:5173"
    ENVIRONMENT: Literal["local", "staging", "production"] = "local"
    GOOGLE_OAUTH_CLIENT_ID: str | None = None
    GOOGLE_OAUTH_CLIENT_SECRET: str | None = None
    GITHUB_OAUTH_CLIENT_ID: str | None = None
    GITHUB_OAUTH_CLIENT_SECRET: str | None = None
    FACEBOOK_OAUTH_CLIENT_ID: str | None = None
    FACEBOOK_OAUTH_CLIENT_SECRET: str | None = None

    BACKEND_CORS_ORIGINS: Annotated[
        list[AnyUrl] | str, BeforeValidator(parse_cors)
    ] = []

    @computed_field  # type: ignore[prop-decorator]
    @property
    def all_cors_origins(self) -> list[str]:
        return [str(origin).rstrip("/") for origin in self.BACKEND_CORS_ORIGINS] + [
            self.FRONTEND_HOST
        ]

    PROJECT_NAME: str
    SENTRY_DSN: HttpUrl | None = None
    POSTGRES_SERVER: str
    POSTGRES_PORT: int = 5432
    POSTGRES_USER: str
    POSTGRES_PASSWORD: str = ""
    POSTGRES_DB: str = ""

    # Rate limiting — see app/core/rate_limit.py.
    #
    # Disabled in tests via env var so the suite's hot loops don't trip
    # 429s. In-memory storage by default; for multi-worker production
    # set RATE_LIMIT_STORAGE_URI to a shared backend (e.g. redis://...)
    # so workers can't each hand out the full per-bucket allowance.
    RATE_LIMIT_ENABLED: bool = True
    RATE_LIMIT_STORAGE_URI: str | None = None

    # Ingestion scheduler — see app/services/scheduler.py.
    #
    # Disabled by default in local because dev-mode auto-reloads would
    # otherwise restart ingestion on every file save. Set it to True in
    # local explicitly when you want to test the scheduled path.
    # Deployed environments default to enabled.
    INGEST_SCHEDULER_ENABLED: bool | None = None
    INGEST_INTERVAL_MINUTES: int = 30
    # Delay before the first run after process startup. Gives the DB,
    # the embedding model load, and any other startup work time to settle
    # before we hammer the configured RSS feeds and start writing rows.
    INGEST_INITIAL_DELAY_SECONDS: int = 60

    @computed_field  # type: ignore[prop-decorator]
    @property
    def ingest_scheduler_enabled(self) -> bool:
        """Resolved scheduler-on flag with environment-aware default.

        If the env var is set explicitly (True or False), use it.
        Otherwise: enabled in non-local environments, disabled in local.
        """
        if self.INGEST_SCHEDULER_ENABLED is not None:
            return self.INGEST_SCHEDULER_ENABLED
        return self.ENVIRONMENT != "local"

    @computed_field  # type: ignore[prop-decorator]
    @property
    def SQLALCHEMY_DATABASE_URI(self) -> PostgresDsn:
        return PostgresDsn.build(
            scheme="postgresql+psycopg",
            username=self.POSTGRES_USER,
            password=self.POSTGRES_PASSWORD,
            host=self.POSTGRES_SERVER,
            port=self.POSTGRES_PORT,
            path=self.POSTGRES_DB,
        )

    SMTP_TLS: bool = True
    SMTP_SSL: bool = False
    SMTP_PORT: int = 587
    SMTP_HOST: str | None = None
    SMTP_USER: str | None = None
    SMTP_PASSWORD: str | None = None
    EMAILS_FROM_EMAIL: EmailStr | None = None
    EMAILS_FROM_NAME: str | None = None

    # Resend (https://resend.com) — provider for the daily digest email.
    # Independent of SMTP_* (those still drive password-reset transactional
    # mail via the existing app.utils.send_email path). When unset, the
    # digest scheduler logs and skips rather than failing — useful for
    # local development where you don't want to wire up an account.
    RESEND_API_KEY: str | None = None
    # Sender for digest emails. Should be a verified domain mailbox in
    # Resend. Falls back to EMAILS_FROM_EMAIL so the same identity used
    # for transactional mail can be reused for the digest if not split.
    DIGEST_FROM_EMAIL: EmailStr | None = None
    # Hour of the day (0–23, in the user's local timezone) the digest
    # is delivered. The hourly scheduler matches this against each
    # user's local clock; staying configurable lets us shift the
    # send window without a code change.
    DIGEST_SEND_LOCAL_HOUR: int = 8

    @model_validator(mode="after")
    def _set_default_emails_from(self) -> Self:
        if not self.EMAILS_FROM_NAME:
            self.EMAILS_FROM_NAME = self.PROJECT_NAME
        return self

    EMAIL_RESET_TOKEN_EXPIRE_HOURS: int = 48

    @computed_field  # type: ignore[prop-decorator]
    @property
    def emails_enabled(self) -> bool:
        return bool(self.SMTP_HOST and self.EMAILS_FROM_EMAIL)

    @computed_field  # type: ignore[prop-decorator]
    @property
    def digest_email_enabled(self) -> bool:
        """Whether the daily-digest sender has the credentials it needs.

        The scheduler checks this on every fire and short-circuits when
        false, so a dev environment without Resend credentials silently
        skips digest delivery instead of crashing the job.
        """
        from_email = self.DIGEST_FROM_EMAIL or self.EMAILS_FROM_EMAIL
        return bool(self.RESEND_API_KEY and from_email)

    EMAIL_TEST_USER: EmailStr = "test@example.com"
    FIRST_SUPERUSER: EmailStr
    FIRST_SUPERUSER_PASSWORD: str

    def _check_default_secret(self, var_name: str, value: str | None) -> None:
        if value == "changethis":
            message = (
                f'The value of {var_name} is "changethis", '
                "for security, please change it, at least for deployments."
            )
            if self.ENVIRONMENT == "local":
                warnings.warn(message, stacklevel=1)
            else:
                raise ValueError(message)

    @model_validator(mode="after")
    def _enforce_non_default_secrets(self) -> Self:
        self._check_default_secret("SECRET_KEY", self.SECRET_KEY)
        self._check_default_secret("POSTGRES_PASSWORD", self.POSTGRES_PASSWORD)
        self._check_default_secret(
            "FIRST_SUPERUSER_PASSWORD", self.FIRST_SUPERUSER_PASSWORD
        )

        return self


settings = Settings()  # type: ignore
