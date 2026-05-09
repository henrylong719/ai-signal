# AI Signal Launch Checklist

Use this as a short production-readiness pass before a public launch.

## Product And SEO

- Confirm `frontend/index.html` title, description, favicon, Open Graph, and social image match the production brand.
- Confirm `frontend/public/robots.txt` and `frontend/public/sitemap.xml` point at the production domain.
- Smoke test the home feed, source directory, source/category/search feeds, article redirects, saved articles, and personalized feed.

## Legal And Contact

- Confirm privacy, terms, accessibility, cookies, contact, and source policy pages are reachable from the footer.
- Replace `CONTACT_EMAIL` in `frontend/src/lib/legal.ts` with the production support address.
- Verify password reset and transactional emails use the intended sender address.

## Security And Admin

- Confirm admin routes and ingestion endpoints require a superuser.
- Set strong production values for `SECRET_KEY`, `FIRST_SUPERUSER_PASSWORD`, and `POSTGRES_PASSWORD`.
- Review `BACKEND_CORS_ORIGINS` and `FRONTEND_HOST` for the production frontend domain.
- Enable shared rate-limit storage with `RATE_LIMIT_STORAGE_URI` for multi-worker deployments.

## Data And Ingestion

- Run `uv run alembic upgrade head` against the production database before serving traffic.
- Confirm pgvector is available and article embedding migrations have run.
- Trigger a supervised ingestion run and review the ingest-runs admin page.
- Decide whether `INGEST_SCHEDULER_ENABLED` should be explicit for the target environment.

## Deployment Smoke Test

- Backend health check returns 200 at `/api/v1/utils/health-check/`.
- OpenAPI docs load at `/docs` for the backend domain.
- Frontend build uses the production `VITE_API_URL`.
- Login, refresh, logout, password reset, and OAuth providers work with production redirect URLs.
- Generated API client is current after any backend schema changes.
