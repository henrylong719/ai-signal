# AI Signal

AI Signal is a full-stack AI knowledge and research dashboard for developers, students, researchers, and builders who want to stay up to date with the fast-moving AI ecosystem.

It ingests updates from curated AI labs, research sources, engineering blogs, newsletters, media outlets, release feeds, and trusted independent writers, then organizes them into a focused reading experience with search, source/category filters, saved articles, followed sources, and personalized recommendations.

AI Signal’s goal is to help users find the signal in the noise: important AI updates, practical engineering knowledge, and emerging trends across areas like AI agents, LLMs, RAG, MCP, voice agents, model tooling, evaluations, and AI engineering practices.

## Features

- Latest article feed with infinite scrolling
- Personalized For You feed for signed-in users
- Recommendation signals from saved articles, outbound clicks, dismissed articles, selected categories, and custom interest tags
- Semantic ranking with pgvector article embeddings and cached user interest vectors
- Search, category feeds, and source-specific feeds
- Source directory grouped across official, independent, community, research, media, and newsletter feeds
- Saved articles page
- Authentication, account settings, password recovery, and admin user management
- Superuser RSS/Atom ingestion endpoint for configured sources
- Superuser article embedding backfill endpoint and CLI script
- Generated TypeScript API client from the FastAPI OpenAPI schema

## Tech Stack

**Frontend**

- React 19
- TypeScript
- Vite
- TanStack Router
- TanStack Query
- Tailwind CSS
- Radix UI
- Biome
- Playwright
- Bun workspace scripts

**Backend**

- FastAPI
- SQLModel
- PostgreSQL with pgvector
- Alembic
- Pydantic Settings
- sentence-transformers
- uv

**Local Infrastructure**

- Docker Compose
- Traefik for local/prod-style routing
- Adminer for database inspection
- Mailcatcher for local email testing

## Project Structure

```text
.
├── backend/              # FastAPI app, models, routes, migrations, services, tests
├── frontend/             # React/Vite app, routes, components, hooks, generated client
├── scripts/              # Root helper scripts, including API client generation
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
PROJECT_NAME=ai-signal
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
```

Frontend API URL:

```env
VITE_API_URL=http://localhost:8000
```

Change secret values before deploying anywhere outside local development.

The contact/legal pages use the public contact email configured in `frontend/src/lib/legal.ts`. Update it before launch if the project should use a branded address.

Optional rate-limiting configuration (defaults are production-safe):

```env
# Turn the per-route limiter off (e.g. for tests). Defaults to True.
RATE_LIMIT_ENABLED=true
# Shared backend so multi-worker deployments don't multiply each
# bucket by the worker count. None ⇒ in-memory (fine for single-worker).
RATE_LIMIT_STORAGE_URI=
```

Per-route limits (per authenticated user when signed in, per IP otherwise):

| Endpoint                         | Limit        |
| -------------------------------- | ------------ |
| `GET /api/v1/articles/`          | 60 / minute  |
| `GET /api/v1/articles/for-you`   | 100 / minute |
| `GET /api/v1/articles/following` | 100 / minute |
| `GET /api/v1/articles/saved/`    | 100 / minute |

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
- Mailcatcher: `http://localhost:1080`
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
```

Regenerate the frontend API client after backend OpenAPI changes:

```bash
bash ./scripts/generate-client.sh
```

Run this after adding or changing backend endpoints, request/response schemas, or auth behavior the frontend consumes. The script exports the FastAPI OpenAPI schema, regenerates `frontend/src/client`, and runs the frontend lint command. If you already have `frontend/openapi.json`, the lower-level command is `cd frontend && bun run generate-client`.

## Articles and Sources

Sources are configured in `backend/app/schemas/source.py`. Each source has an RSS/Atom URL, default category, source type, topic, and description.

The superuser-only ingestion endpoint imports from all configured sources:

```http
POST /api/v1/ingest
```

The scheduler lives in `backend/app/services/scheduler.py`. It is disabled by default when `ENVIRONMENT=local`, enabled by default for staging/production, and can be controlled with `INGEST_SCHEDULER_ENABLED`, `INGEST_INTERVAL_MINUTES`, and `INGEST_INITIAL_DELAY_SECONDS`.

Article API highlights:

- `GET /api/v1/articles/` for latest articles with optional `category`, `source`, and `search` filters
- `GET /api/v1/articles/for-you` for the signed-in user's personalized feed
- `GET /api/v1/articles/sources/` for configured source metadata
- `GET /api/v1/articles/saved/` and `GET /api/v1/articles/saved/ids` for saved articles
- `POST /api/v1/articles/{article_id}/save` and `DELETE /api/v1/articles/{article_id}/save`
- `GET /api/v1/articles/{article_id}/go` to log a signed-in click and redirect to the original URL
- `POST /api/v1/articles/{article_id}/dismiss` to hide an article from For You

## Personalization

The For You feed combines explicit interests, saved-article tags and sources, clicked tags and sources, article recency, and optional semantic similarity.

Embeddings use `sentence-transformers/all-MiniLM-L6-v2` dimensions and are stored in pgvector columns. Article embeddings can be backfilled through the superuser endpoint:

```http
POST /api/v1/admin/embed-articles
```

For large backfills, use the backend CLI script in `backend/app/script/backfill_embeddings.py`.

User interest preferences are managed through:

```http
GET /api/v1/users/me/interests
PUT /api/v1/users/me/interests
```

## Documentation

- Backend details: [backend/README.md](backend/README.md)
- Frontend details: [frontend/README.md](frontend/README.md)
- Local development notes: [development.md](development.md)
- Deployment notes: [deployment.md](deployment.md)
- Launch checklist: [docs/launch-checklist.md](docs/launch-checklist.md)
