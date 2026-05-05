# AI Signal

AI Signal is a full-stack AI engineering news dashboard. It collects article metadata from trusted AI blogs, research labs, engineering teams, newsletters, and community sources, then organizes those articles into a focused feed for builders who want to follow practical AI updates.

The app is built around discovery rather than replacing original sources. Articles link back to the original post, paper, repository, or announcement.

## Features

- Curated AI article feed with infinite scrolling
- Filtering by topic category, source, and search query
- Source directory for official, independent, community, and research feeds
- Saved articles for signed-in users
- Authentication, account settings, and admin user management
- RSS ingestion endpoint for importing articles from configured sources
- Generated TypeScript API client from the FastAPI OpenAPI schema
- For You page prepared for future personalized recommendations

## Tech Stack

**Frontend**

- React
- TypeScript
- Vite
- TanStack Router
- TanStack Query
- Tailwind CSS
- Radix UI
- Playwright

**Backend**

- FastAPI
- SQLModel
- PostgreSQL
- Alembic
- Pydantic Settings
- uv

**Infrastructure**

- Docker Compose
- Traefik for local/prod-style routing
- Adminer for database inspection
- Mailcatcher for local email testing

## Project Structure

```text
.
├── backend/              # FastAPI app, SQLModel models, API routes, migrations, tests
├── frontend/             # React/Vite app, routes, components, generated API client
├── scripts/              # Root helper scripts, including API client generation
├── compose.yml           # Docker Compose services
├── compose.override.yml  # Local development Compose overrides
├── package.json          # Bun workspace scripts for the frontend
└── pyproject.toml        # uv workspace configuration for the backend
```

## Prerequisites

- [Bun](https://bun.sh/) for frontend dependencies and scripts
- [uv](https://docs.astral.sh/uv/) for backend dependencies
- [Docker](https://www.docker.com/) for PostgreSQL and full-stack local services

## Environment

The backend reads configuration from the root `.env` file. At minimum, local development needs values for:

```env
PROJECT_NAME=AI Signal
SECRET_KEY=changethis
FIRST_SUPERUSER=admin@example.com
FIRST_SUPERUSER_PASSWORD=changethis
POSTGRES_SERVER=localhost
POSTGRES_PORT=5432
POSTGRES_DB=app
POSTGRES_USER=postgres
POSTGRES_PASSWORD=changethis
FRONTEND_HOST=http://localhost:5173
BACKEND_CORS_ORIGINS=http://localhost:5173
```

Change the secret values before deploying anywhere outside local development.

## Quick Start

Install dependencies:

```bash
bun install
cd backend
uv sync
```

Start PostgreSQL from the repository root:

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

The API is available at `http://localhost:8000`, and the OpenAPI docs are available at `http://localhost:8000/docs`.

## Docker Compose

To run the local stack with Docker Compose:

```bash
docker compose up -d --wait
```

Useful local services:

- Frontend: `http://localhost:5173`
- Backend API: `http://localhost:8000`
- Adminer: `http://localhost:8080`
- Mailcatcher: `http://localhost:1080`

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
cd frontend && bun run build
```

Backend commands from `backend/`:

```bash
uv sync
bash ./scripts/lint.sh
bash ./scripts/test.sh
```

Regenerate the frontend API client after backend OpenAPI changes:

```bash
bash ./scripts/generate-client.sh
```

## Article Ingestion

Article sources are configured in `backend/app/schemas/source.py`. The protected ingestion endpoint imports from those RSS/Atom feeds:

```http
POST /api/v1/ingest
```

The endpoint requires a superuser account.

## Documentation

- Backend details: [backend/README.md](backend/README.md)
- Frontend details: [frontend/README.md](frontend/README.md)
- Local development notes: [development.md](development.md)

## Roadmap

- Personalized recommendations for the For You page
- Better interest and topic preference signals
- More source quality controls
- Richer article ranking and discovery tools
