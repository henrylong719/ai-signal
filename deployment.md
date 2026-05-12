# AI Signal Deployment

AI Signal can be deployed with Docker Compose behind Traefik. The checked-in Compose files assume separate frontend and backend domains, for example `dashboard.example.com` and `api.example.com`.

## Prerequisites

- A server with Docker Engine installed.
- DNS records for the frontend, API, Traefik dashboard, and any staging domains.
- A `traefik-public` Docker network, unless you adapt `compose.yml`.
- Production values for all required environment variables.

## Required Environment

Set these for each deployed environment:

```bash
export ENVIRONMENT=production
export DOMAIN=example.com
export STACK_NAME=ai-signal-production
export SECRET_KEY="replace-with-generated-secret"
export FIRST_SUPERUSER=admin@example.com
export FIRST_SUPERUSER_PASSWORD="replace-with-generated-secret"
export POSTGRES_PASSWORD="replace-with-generated-secret"
export BACKEND_CORS_ORIGINS="https://dashboard.${DOMAIN},https://api.${DOMAIN}"
export FRONTEND_HOST="https://dashboard.${DOMAIN}"
```

Generate secrets with:

```bash
python -c "import secrets; print(secrets.token_urlsafe(32))"
```

Common optional values:

- `RESEND_API_KEY`, `EMAILS_FROM_EMAIL`, `EMAILS_FROM_NAME`, and `DIGEST_FROM_EMAIL` for app email.
- `SENTRY_DSN` for backend error reporting.
- `RATE_LIMIT_STORAGE_URI` for shared rate-limit storage in multi-worker deployments.
- `INGEST_SCHEDULER_ENABLED`, `INGEST_INTERVAL_MINUTES`, and `INGEST_INITIAL_DELAY_SECONDS` for scheduled ingestion.

The frontend build receives `VITE_API_URL=https://api.${DOMAIN}` from `compose.yml`.

## Deploy With Docker Compose

From the deployed application directory:

```bash
docker compose -f compose.yml build
docker compose -f compose.yml up -d
```

Do not include `compose.override.yml` for production; it is local-development-only.

## Database And Migrations

The `prestart` service runs before the backend and applies Alembic migrations. For manual checks:

```bash
docker compose -f compose.yml run --rm prestart
docker compose -f compose.yml exec backend alembic current
```

Confirm pgvector migrations have run before enabling feeds that depend on embeddings.

## GitHub Actions

The deployment workflows expect self-hosted runners labeled `staging` and `production`. Configure these repository or environment secrets:

- `DOMAIN_PRODUCTION`
- `DOMAIN_STAGING`
- `STACK_NAME_PRODUCTION`
- `STACK_NAME_STAGING`
- `SECRET_KEY`
- `FIRST_SUPERUSER`
- `FIRST_SUPERUSER_PASSWORD`
- `POSTGRES_PASSWORD`
- `RESEND_API_KEY`
- `EMAILS_FROM_EMAIL`
- `EMAILS_FROM_NAME`
- `DIGEST_FROM_EMAIL`
- `SENTRY_DSN`

## Post-Deploy Smoke Test

- Frontend loads on the dashboard domain.
- Backend health check returns 200 at `/api/v1/utils/health-check/`.
- OpenAPI docs load on the API domain.
- Login, refresh, logout, and password reset work.
- Superuser-only admin and ingestion routes are protected.
- A supervised ingestion run completes and articles appear in the feed.
- `robots.txt`, `sitemap.xml`, and social metadata match the production domain.
