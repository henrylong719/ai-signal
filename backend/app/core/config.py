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
    SECRET_KEY: str = "changethis"
    # 15-minute access token, refreshed via the refresh cookie. Pre-cookie-auth
    # this was 8 days (60 * 24 * 8) because there was no refresh path — losing
    # the token meant logging back in. With refresh tokens, the access token
    # only needs to live long enough that we're not refreshing on every
    # request. 15 minutes is the conventional sweet spot.
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 15
    REFRESH_TOKEN_EXPIRE_DAYS: int = 30
    FRONTEND_HOST: str = "http://localhost:5173"
    # Public origin of the FastAPI backend, used to build absolute API URLs
    # in emails (article click-throughs plus unsubscribe links). When unset we
    # fall back to ``FRONTEND_HOST + API_V1_STR``, which is correct only
    # when frontend and backend share an origin via a reverse proxy or
    # platform rewrite. Set this whenever the API lives on a distinct
    # host (e.g. ``https://api.aisignal.now``) — or in local dev where
    # the Vite server on :5173 has no API proxy.
    BACKEND_PUBLIC_URL: str | None = None
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
    # Full database URL — preferred for managed providers like Neon that
    # hand out a connection string with query params (e.g. sslmode=require).
    # When set, takes precedence over the split POSTGRES_* vars below.
    DATABASE_URL: str | None = None
    POSTGRES_SERVER: str = ""
    POSTGRES_PORT: int = 5432
    POSTGRES_USER: str = ""
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

    # Embedding provider — see app/services/embeddings.py.
    #
    # Article and user-interest embeddings are computed by calling the
    # OpenAI Embeddings API. We deliberately keep the on-disk vector
    # dimension at 384 (Matryoshka truncation) so the existing pgvector
    # column doesn't need a schema change. If you ever raise this number
    # you must also widen the column and re-embed every article.
    OPENAI_API_KEY: str | None = None
    OPENAI_EMBEDDING_MODEL: str = "text-embedding-3-small"
    OPENAI_EMBEDDING_DIMENSIONS: int = 384
    # Override only when proxying through a gateway (e.g. Vercel AI
    # Gateway, an Azure deployment). The default points at OpenAI direct.
    OPENAI_BASE_URL: str = "https://api.openai.com/v1"

    # Ingestion scheduler — see app/services/scheduler.py.
    #
    # Disabled by default in local because dev-mode auto-reloads would
    # otherwise restart ingestion on every file save. Set it to True in
    # local explicitly when you want to test the scheduled path.
    # Deployed environments default to enabled.
    INGEST_SCHEDULER_ENABLED: bool | None = None
    INGEST_INTERVAL_MINUTES: int = 60
    # Delay before the first run after process startup. Gives the DB
    # pool and any other startup work time to settle before we hammer
    # the configured RSS feeds and start writing rows.
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

    # Article cleanup — see app/services/article_cleanup.py. Two-stage
    # safe pipeline: archive old unsaved/unengaged articles first, then
    # delete archived rows that have stayed quiet for an additional
    # window. DRY_RUN defaults to True so the first real fire (manual
    # script, cron endpoint, scheduler) only reports counts; an operator
    # has to flip the flag once they've inspected the numbers.
    ARTICLE_CLEANUP_ENABLED: bool = True
    ARTICLE_CLEANUP_DRY_RUN: bool = True
    ARTICLE_ARCHIVE_AFTER_DAYS: int = 90
    ARTICLE_DELETE_AFTER_DAYS: int = 180
    ARTICLE_KEEP_CLICKED_AFTER_DAYS: int = 180
    ARTICLE_CLEANUP_BATCH_SIZE: int = 500
    # Shared secret for the protected /internal/article-cleanup endpoint.
    # Unset in non-local environments disables the endpoint (503) so a
    # misconfigured deploy can't accidentally expose destructive cleanup
    # to the internet.
    ARTICLE_CLEANUP_CRON_SECRET: str | None = None
    # Like INGEST_SCHEDULER_ENABLED: explicit value wins, otherwise
    # enabled in non-local. Pair with ARTICLE_CLEANUP_DRY_RUN=True (the
    # default) for a safe first deployment.
    ARTICLE_CLEANUP_SCHEDULER_ENABLED: bool | None = None
    ARTICLE_CLEANUP_SCHEDULE_HOUR_UTC: int = 3

    @computed_field  # type: ignore[prop-decorator]
    @property
    def article_cleanup_scheduler_enabled(self) -> bool:
        """Resolved cleanup scheduler flag.

        Explicit env value wins. Otherwise enabled in non-local
        environments, disabled in local — same shape as the ingest
        scheduler so dev-mode auto-reloads don't fire cleanup on every
        file save.
        """
        if self.ARTICLE_CLEANUP_SCHEDULER_ENABLED is not None:
            return self.ARTICLE_CLEANUP_SCHEDULER_ENABLED
        return self.ENVIRONMENT != "local"

    @computed_field  # type: ignore[prop-decorator]
    @property
    def SQLALCHEMY_DATABASE_URI(self) -> PostgresDsn | str:
        if self.DATABASE_URL:
            # SQLAlchemy needs the driver in the scheme. Neon (and most
            # managed Postgres providers) hand out plain `postgresql://`
            # URLs; rewrite the prefix once and otherwise pass the URL
            # through verbatim so query params like `sslmode=require`
            # survive untouched.
            if self.DATABASE_URL.startswith("postgresql://"):
                return (
                    "postgresql+psycopg://" + self.DATABASE_URL[len("postgresql://") :]
                )
            return self.DATABASE_URL
        return PostgresDsn.build(
            scheme="postgresql+psycopg",
            username=self.POSTGRES_USER,
            password=self.POSTGRES_PASSWORD,
            host=self.POSTGRES_SERVER,
            port=self.POSTGRES_PORT,
            path=self.POSTGRES_DB,
        )

    # --- Email -------------------------------------------------------------
    #
    # All app email — password reset, account/system, and the daily
    # digest — flows through Resend (https://resend.com). The unified
    # service lives in ``app.services.email``; the low-level HTTP
    # wrapper in ``app.services.resend_email``. Set ``RESEND_API_KEY``
    # plus ``EMAILS_FROM_EMAIL`` and the ``aisignal.now`` domain (or
    # whatever you've verified in Resend) to enable sending. When
    # ``RESEND_API_KEY`` is unset, callers log a warning and skip
    # sending instead of crashing — used in local dev to avoid having
    # to wire up an account.
    RESEND_API_KEY: str | None = None
    # Default ``From:`` for app email. Must be a verified domain
    # mailbox in Resend. Recommended:
    # ``EMAILS_FROM_EMAIL=hello@aisignal.now``.
    EMAILS_FROM_EMAIL: EmailStr | None = None
    # Display name in the ``From:`` header. Defaults to PROJECT_NAME
    # via ``_set_default_emails_from`` below so a deploy that only
    # sets EMAILS_FROM_EMAIL still gets a friendly sender label.
    EMAILS_FROM_NAME: str | None = None
    # Sender for the daily digest. When set, bulk traffic goes from a
    # dedicated mailbox (e.g. ``digest@aisignal.now``) so a digest
    # deliverability issue can't degrade transactional reputation.
    # Falls back to ``EMAILS_FROM_EMAIL`` when unset, which is fine
    # for small deployments that haven't split senders yet.
    DIGEST_FROM_EMAIL: EmailStr | None = None
    # Hour of the day (0–23, in the user's local timezone) the digest
    # is delivered. The hourly scheduler matches this against each
    # user's local clock; staying configurable lets us shift the
    # send window without a code change.
    DIGEST_SEND_LOCAL_HOUR: int = 6

    # --- SMTP (legacy / deprecated) ---------------------------------------
    #
    # Pre-Resend, transactional mail went out over SMTP via the
    # ``emails`` PyPI package. Kept around for backward compatibility
    # so existing ``.env`` files with SMTP_* set don't break Settings
    # validation. Nothing in the running app reads them; remove them
    # from your environment whenever you next rotate it.
    SMTP_TLS: bool = True
    SMTP_SSL: bool = False
    SMTP_PORT: int = 587
    SMTP_HOST: str | None = None
    SMTP_USER: str | None = None
    SMTP_PASSWORD: str | None = None

    @model_validator(mode="after")
    def _set_default_emails_from(self) -> Self:
        if not self.EMAILS_FROM_NAME:
            self.EMAILS_FROM_NAME = self.PROJECT_NAME
        return self

    EMAIL_RESET_TOKEN_EXPIRE_HOURS: int = 48

    @computed_field  # type: ignore[prop-decorator]
    @property
    def emails_enabled(self) -> bool:
        """Whether transactional email is wired up.

        True iff Resend credentials and a default sender are present.
        Old SMTP_* values are intentionally ignored — they no longer
        drive any send path.
        """
        return bool(self.RESEND_API_KEY and self.EMAILS_FROM_EMAIL)

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
    def _require_database_config(self) -> Self:
        # Either a full DATABASE_URL or the split POSTGRES_* vars must
        # be supplied — otherwise SQLALCHEMY_DATABASE_URI would silently
        # build a URL with empty host/user.
        if not self.DATABASE_URL and not (self.POSTGRES_SERVER and self.POSTGRES_USER):
            raise ValueError(
                "Database is not configured: set DATABASE_URL, or both "
                "POSTGRES_SERVER and POSTGRES_USER."
            )
        return self

    @model_validator(mode="after")
    def _enforce_non_default_secrets(self) -> Self:
        self._check_default_secret("SECRET_KEY", self.SECRET_KEY)
        self._check_default_secret("POSTGRES_PASSWORD", self.POSTGRES_PASSWORD)
        self._check_default_secret(
            "FIRST_SUPERUSER_PASSWORD", self.FIRST_SUPERUSER_PASSWORD
        )

        return self


settings = Settings()  # type: ignore
