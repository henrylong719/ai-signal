# AI Signal Backend

The backend is a FastAPI app with SQLModel, PostgreSQL/pgvector, Alembic migrations, RSS/Atom ingestion, authentication, admin endpoints, and generated OpenAPI docs.

## Requirements

- [uv](https://docs.astral.sh/uv/)
- Docker, when using the local PostgreSQL/pgvector service

## Local Setup

From the repository root:

```bash
cp .env.example .env
docker compose up -d db
```

From `backend/`:

```bash
uv sync
uv run bash scripts/prestart.sh
uv run fastapi dev app/main.py
```

The API runs at `http://localhost:8000`, with OpenAPI docs at `http://localhost:8000/docs`.

## Environment

The backend reads `../.env`. Required local values include:

- `PROJECT_NAME`
- `SECRET_KEY`
- `FIRST_SUPERUSER`
- `FIRST_SUPERUSER_PASSWORD`
- `POSTGRES_SERVER`
- `POSTGRES_PORT`
- `POSTGRES_DB`
- `POSTGRES_USER`
- `POSTGRES_PASSWORD`
- `FRONTEND_HOST`
- `BACKEND_CORS_ORIGINS`

Optional production or feature-specific values include SMTP settings, OAuth provider credentials, `SENTRY_DSN`, `RATE_LIMIT_STORAGE_URI`, and ingestion scheduler settings. See the root `.env.example` for the full list.

## Database And Migrations

`scripts/prestart.sh` waits for the database, runs migrations, and creates the initial superuser from the environment.

Useful commands from `backend/`:

```bash
uv run alembic upgrade head
uv run alembic revision --autogenerate -m "Describe schema change"
uv run bash scripts/prestart.sh
```

To reset local database data:

```bash
docker compose down -v
```

## Ingestion And Scheduler

Sources are configured in `backend/app/schemas/source.py`. Superusers can trigger ingestion with:

```http
POST /api/v1/ingest
```

The scheduler is disabled by default for `ENVIRONMENT=local` to avoid repeated dev-server reload ingestion. It defaults to enabled for staging and production. Configure it with:

- `INGEST_SCHEDULER_ENABLED`
- `INGEST_INTERVAL_MINUTES`
- `INGEST_INITIAL_DELAY_SECONDS`

## Embeddings

Article embeddings use `sentence-transformers/all-MiniLM-L6-v2` dimensions and pgvector storage. Superusers can backfill article embeddings through:

```http
POST /api/v1/admin/embed-articles
```

For larger local backfills, use `backend/app/script/backfill_embeddings.py`.

## Commands

From `backend/`:

```bash
uv sync
bash ./scripts/lint.sh
bash ./scripts/test.sh
```

When running tests, the suite forces a test database name via `TEST_POSTGRES_DB` or by deriving one from `POSTGRES_DB`.

## Email And OAuth

Password recovery email is enabled when both `SMTP_HOST` and `EMAILS_FROM_EMAIL` are set. Local Docker Compose uses Mailcatcher at `http://localhost:1080`.

OAuth providers use backend callback URLs:

```text
http://localhost:8000/api/v1/login/google/callback
http://localhost:8000/api/v1/login/github/callback
http://localhost:8000/api/v1/login/facebook/callback
```
