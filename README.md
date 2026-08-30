# AI Signal

AI Signal is a full-stack AI knowledge and research dashboard for developers, students, researchers, and builders who want to stay up to date with the fast-moving AI ecosystem.

It ingests updates from ~170 curated AI labs, research sources, engineering blogs, newsletters, media outlets, release feeds, and trusted independent writers, then organizes them into a focused reading experience with search, source/category filters, saved articles, followed sources, a daily digest email, and personalized recommendations.

AI Signal’s goal is to help users find the signal in the noise: important AI updates, practical engineering knowledge, and emerging trends across areas like AI agents, LLMs, RAG, MCP, voice agents, model tooling, evaluations, and AI engineering practices.

## Features

**Reading**

- Latest article feed with infinite scrolling
- Personalized For You feed for signed-in users
- Keyword and semantic search, category feeds, and source-specific feeds
- Source directory grouped across official, independent, community, research, media, newsletter, analysis, policy, education, papers, podcast, and video feeds
- Saved articles page and a Following feed for followed sources
- Today's Digest page plus an emailed daily digest

**Personalization**

- Recommendation signals from saved articles, outbound clicks, dismissed articles, selected categories, and custom interest tags
- Semantic ranking with pgvector article embeddings and cached user interest vectors
- Exponential recency decay on behavioral signals, so old saves/clicks fade
- MMR diversity reranking so a single bursty source can't flood the feed
- ε-greedy exploration slots so the feed doesn't collapse into one topic
- Explainable scoring — each article carries a score breakdown that powers "Because you follow X" labels

**Accounts**

- Email/password auth with short-lived access tokens and refresh-cookie sessions
- Optional Google, GitHub, and Facebook OAuth
- First-run onboarding, account settings, digest preferences, password recovery, and account deletion
- Anonymous email subscriptions (digest without an account) with unsubscribe/resubscribe flows

**Operations**

- Scheduled RSS/Atom ingestion (APScheduler) plus a superuser ingestion endpoint
- Admin pages for articles, ingest runs, guest funnel analytics, and digest email preview
- Superuser article embedding backfill endpoint and CLI script
- Two-stage article cleanup (archive → delete) with dry-run default, scheduler, and a secret-protected internal endpoint
- Per-route rate limiting
- Generated TypeScript API client from the FastAPI OpenAPI schema

## Tech Stack

**Frontend**

- React 19
- TypeScript
- Vite
- TanStack Router / Query / Table
- Tailwind CSS v4
- Radix UI
- React Hook Form + Zod
- Biome
- Playwright
- Bun workspace scripts

**Backend**

- FastAPI
- SQLModel
- PostgreSQL with pgvector
- Alembic
- Pydantic Settings
- APScheduler (ingest, digest, cleanup jobs)
- SlowAPI (rate limiting)
- feedparser (RSS/Atom)
- OpenAI Embeddings API (`text-embedding-3-small`, 384 dimensions)
- Resend (transactional and digest email)
- PyJWT + pwdlib (argon2/bcrypt)
- Sentry (optional)
- uv

**Local Infrastructure**

- Docker Compose
- Traefik for local/prod-style routing
- Adminer for database inspection

## Project Structure

```text
.
├── backend/              # FastAPI app, models, routes, migrations, services, tests
├── frontend/             # React/Vite app, routes, components, hooks, generated client
├── scripts/              # Root helper scripts, including API client generation
├── docs/                 # Launch checklist and supporting docs
├── compose.yml           # Main Docker Compose services
├── compose.override.yml  # Local development Compose overrides
├── compose.traefik.yml   # Traefik production-style companion config
├── package.json          # Bun workspace scripts for the frontend
└── bun.lock              # Bun lockfile
```

## Prerequisites

- [Bun](https://bun.sh/) for frontend dependencies and workspace scripts
- [uv](https://docs.astral.sh/uv/) for backend dependencies
- [Docker](https://www.docker.com/) for PostgreSQL/pgvector and full-stack local services

## Environment

The backend reads configuration from the root `.env` file. The frontend reads `frontend/.env`.

Create local environment files from the checked-in examples:

```bash
cp .env.example .env
cp frontend/.env.example frontend/.env
```

Important local values:

```env
PROJECT_NAME=AI Signal
ENVIRONMENT=local
SECRET_KEY=changethis
FIRST_SUPERUSER=admin@example.com
FIRST_SUPERUSER_PASSWORD=changethis
POSTGRES_SERVER=localhost
POSTGRES_PORT=5432
POSTGRES_DB=app
POSTGRES_USER=postgres
POSTGRES_PASSWORD=changethis
FRONTEND_HOST=http://localhost:5173
BACKEND_CORS_ORIGINS=http://localhost,http://localhost:5173
BACKEND_PUBLIC_URL=http://localhost:8000
```

Frontend API URL:

```env
VITE_API_URL=http://localhost:8000
```

Change secret values before deploying anywhere outside local development.

### Database

Either set the split `POSTGRES_*` vars (local Docker Compose) or a single full connection string, which takes precedence and is the recommended form for managed providers like Neon:

```env
DATABASE_URL=postgresql://USER:PASSWORD@host/dbname?sslmode=require
```

A `postgresql://` scheme is rewritten to `postgresql+psycopg://` automatically, and query params are passed through untouched.

### Embeddings

Semantic ranking and semantic search call the OpenAI Embeddings API. Without a key the app still runs — those layers degrade to keyword/heuristic behavior.

```env
OPENAI_API_KEY=sk-...
OPENAI_EMBEDDING_MODEL=text-embedding-3-small
# Kept at 384 (Matryoshka truncation) to match the existing pgvector column.
# Raising this requires widening the column and re-embedding every article.
OPENAI_EMBEDDING_DIMENSIONS=384
# Override only when proxying through a gateway (Vercel AI Gateway, Azure).
OPENAI_BASE_URL=https://api.openai.com/v1
```

### Email (Resend)

All app email — password reset, account/system mail, and the daily digest — goes through [Resend](https://resend.com). When `RESEND_API_KEY` is unset the app logs a warning and skips sending, which is the intended local-dev behavior.

```env
RESEND_API_KEY=
EMAILS_FROM_EMAIL=hello@aisignal.now
EMAILS_FROM_NAME=AI Signal
# Optional dedicated bulk sender; falls back to EMAILS_FROM_EMAIL.
DIGEST_FROM_EMAIL=digest@aisignal.now
DIGEST_SEND_LOCAL_HOUR=6
SUBSCRIBER_DIGEST_SEND_HOUR_UTC=6
```

The `SMTP_*` variables are legacy and no longer read by the app; they are only tolerated so old environments still validate.

### OAuth (optional)

```env
GOOGLE_OAUTH_CLIENT_ID=
GOOGLE_OAUTH_CLIENT_SECRET=
GITHUB_OAUTH_CLIENT_ID=
GITHUB_OAUTH_CLIENT_SECRET=
FACEBOOK_OAUTH_CLIENT_ID=
FACEBOOK_OAUTH_CLIENT_SECRET=
```

### Schedulers and cleanup

```env
# Ingest. Unset ⇒ disabled in local, enabled in staging/production.
INGEST_SCHEDULER_ENABLED=
INGEST_INTERVAL_MINUTES=60
INGEST_INITIAL_DELAY_SECONDS=60

# Article cleanup (archive → delete). DRY_RUN defaults to True so the
# first real fire only reports counts.
ARTICLE_CLEANUP_ENABLED=true
ARTICLE_CLEANUP_DRY_RUN=true
ARTICLE_ARCHIVE_AFTER_DAYS=90
ARTICLE_DELETE_AFTER_DAYS=180
ARTICLE_CLEANUP_SCHEDULER_ENABLED=
ARTICLE_CLEANUP_SCHEDULE_HOUR_UTC=3
# Required to enable POST /api/v1/internal/article-cleanup outside local.
ARTICLE_CLEANUP_CRON_SECRET=
```

### Rate limiting

```env
# Turn the per-route limiter off (e.g. for tests). Defaults to True.
RATE_LIMIT_ENABLED=true
# Shared backend so multi-worker deployments don't multiply each
# bucket by the worker count. None ⇒ in-memory (fine for single-worker).
RATE_LIMIT_STORAGE_URI=
```

Per-route limits (per authenticated user when signed in, per IP otherwise):

| Endpoint                                  | Limit        |
| ----------------------------------------- | ------------ |
| `GET /api/v1/articles/`                   | 60 / minute  |
| `GET /api/v1/articles/for-you`            | 100 / minute |
| `GET /api/v1/articles/following`          | 100 / minute |
| `GET /api/v1/articles/saved/`             | 100 / minute |
| `POST /api/v1/analytics/guest-event`      | 120 / minute |
| `POST /api/v1/login/access-token`         | 10 / minute  |
| `POST /api/v1/users/signup`               | 10 / minute  |
| `POST /api/v1/reset-password/`            | 10 / minute  |
| `POST /api/v1/password-recovery/{email}`  | 5 / minute   |
| `POST /api/v1/subscriptions`              | 10 / minute  |
| `POST /api/v1/users/me/feedback`          | 10 / minute  |

The contact/legal pages use the public contact email configured in `frontend/src/lib/legal.ts`. Update it before launch if the project should use a branded address.

## Quick Start

Install dependencies:

```bash
bun install
cd backend
uv sync
```

Start PostgreSQL with pgvector from the repository root:

```bash
docker compose up -d db
```

Initialize the backend database:

```bash
cd backend
uv run bash scripts/prestart.sh
```

Run the backend:

```bash
cd backend
uv run fastapi dev app/main.py
```

In another terminal, run the frontend from the repository root:

```bash
bun run dev
```

Open the app at `http://localhost:5173`.

The API is available at `http://localhost:8000`, and OpenAPI docs are available at `http://localhost:8000/docs`.

## Docker Compose

To run the local stack with Docker Compose:

```bash
docker compose up -d --wait
```

Useful local services:

- Frontend: `http://localhost:5173`
- Backend API: `http://localhost:8000`
- API docs: `http://localhost:8000/docs`
- Adminer: `http://localhost:8080`
- Traefik dashboard: `http://localhost:8090`

To stop the stack:

```bash
docker compose down
```

To reset local database data:

```bash
docker compose down -v
```

## Common Commands

Frontend commands from the repository root:

```bash
bun run dev
bun run lint
bun run test
bun run test:ui
cd frontend && bun run build
```

Backend commands from `backend/`:

```bash
uv sync
bash ./scripts/lint.sh
bash ./scripts/test.sh
uv run alembic revision --autogenerate -m "Describe schema change"
uv run alembic upgrade head
uv run python -m app.script.backfill_embeddings
uv run python -m app.script.cleanup_articles
uv run python scripts/check_sources.py
```

Regenerate the frontend API client after backend OpenAPI changes:

```bash
bash ./scripts/generate-client.sh
```

Run this after adding or changing backend endpoints, request/response schemas, or auth behavior the frontend consumes. The script exports the FastAPI OpenAPI schema, regenerates `frontend/src/client`, and runs the frontend lint command. If you already have `frontend/openapi.json`, the lower-level command is `cd frontend && bun run generate-client`.

## Articles and Sources

Sources are configured in `backend/app/schemas/source.py` (`SOURCES`). Each source has an RSS/Atom URL, default category, source type, topic, and description.

The superuser-only ingestion endpoint imports from all configured sources:

```http
POST /api/v1/ingest
```

Every ingestion — scheduled or manual — goes through the run-tracking wrapper in `backend/app/services/ingest_runner.py`, so each run appears on the admin ingest-runs page.

The scheduler lives in `backend/app/services/scheduler.py`. It is disabled by default when `ENVIRONMENT=local`, enabled by default for staging/production, and registers:

- Ingestion, every `INGEST_INTERVAL_MINUTES`
- The per-user daily digest, hourly on the hour (each user is sent at their local `DIGEST_SEND_LOCAL_HOUR`)
- The anonymous-subscriber digest, daily at `SUBSCRIBER_DIGEST_SEND_HOUR_UTC`
- Refresh-session pruning, daily
- Article cleanup, daily at `ARTICLE_CLEANUP_SCHEDULE_HOUR_UTC` (when enabled)

Article API highlights:

- `GET /api/v1/articles/` for latest articles with optional `category`, `source`, and `search` filters
- `GET /api/v1/articles/for-you` for the signed-in user's personalized feed
- `GET /api/v1/articles/following` for articles from followed sources
- `GET /api/v1/articles/sources/` for configured source metadata
- `GET /api/v1/articles/saved/` and `GET /api/v1/articles/saved/ids` for saved articles
- `POST /api/v1/articles/{article_id}/save` and `DELETE /api/v1/articles/{article_id}/save`
- `GET /api/v1/articles/{article_id}/go` to log a signed-in click and redirect to the original URL
- `POST /api/v1/articles/{article_id}/dismiss` to hide an article from For You

## Personalization

The For You feed combines explicit interests, saved-article tags and sources, clicked tags and sources, article recency, and optional semantic similarity. Scoring is a weighted linear combination of normalized signals in `backend/app/services/recommender.py`, with negative signals (saved, dismissed) applied as hard filters rather than soft penalties. Behavioral signals decay exponentially (`services/decay.py`), the result is reranked for diversity with MMR (`services/diversity.py`), and a fraction of slots is reserved for exploration (`services/exploration.py`).

Embeddings are produced by the OpenAI Embeddings API (`text-embedding-3-small`, truncated to 384 dimensions) and stored in pgvector columns. This replaced the previous in-process `sentence-transformers` model, which pinned ~2 GB of resident memory on the API container. Because vectors from different models aren't comparable, changing `OPENAI_EMBEDDING_MODEL` requires re-embedding every article.

Article embeddings can be backfilled through the superuser endpoint:

```http
POST /api/v1/admin/embed-articles
```

For large backfills, use the backend CLI script in `backend/app/script/backfill_embeddings.py`.

User interest preferences are managed through:

```http
GET /api/v1/users/me/interests
PUT /api/v1/users/me/interests
```

## Digest

Today's Digest is a fixed, time-bounded snapshot of the day's articles organized into computed sections — personalized when there's enough signal, with a non-personalized fallback for cold-start users (`backend/app/services/digest.py`).

```http
GET  /api/v1/digest/today-digest
POST /api/v1/subscriptions            # anonymous email subscription
GET  /api/v1/digest/unsubscribe       # token-based unsubscribe / resubscribe
```

Registered users control delivery via `PUT /api/v1/users/me/digest-preferences`.

## Admin

Superuser-only endpoints (all under `/api/v1/admin`) back the in-app admin pages:

```http
GET    /api/v1/admin/articles
DELETE /api/v1/admin/articles/{article_id}
GET    /api/v1/admin/ingest-runs
GET    /api/v1/admin/analytics/guest-funnel
GET    /api/v1/admin/email-preview/digest-html
POST   /api/v1/admin/embed-articles
```

Article cleanup can also be triggered out-of-band by a cron platform:

```http
POST /api/v1/internal/article-cleanup   # requires ARTICLE_CLEANUP_CRON_SECRET
```

## Documentation

- Backend details: [backend/README.md](backend/README.md)
- Frontend details: [frontend/README.md](frontend/README.md)
- Local development notes: [development.md](development.md)
- Deployment notes: [deployment.md](deployment.md)
- Launch checklist: [docs/launch-checklist.md](docs/launch-checklist.md)
