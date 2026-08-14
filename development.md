# AI Signal Development

## Docker Compose

Create local environment files first:

```bash
cp .env.example .env
cp frontend/.env.example frontend/.env
```

Start the local stack:

```bash
docker compose watch
```

Local URLs:

- Frontend: <http://localhost:5173>
- Backend: <http://localhost:8000>
- OpenAPI docs: <http://localhost:8000/docs>
- ReDoc: <http://localhost:8000/redoc>
- Adminer: <http://localhost:8080>
- Traefik dashboard: <http://localhost:8090>

Useful logs:

```bash
docker compose logs
docker compose logs backend
```

## Running Services Directly

Run only PostgreSQL/pgvector in Docker:

```bash
docker compose up -d db
```

Run the backend locally:

```bash
cd backend
uv sync
uv run bash scripts/prestart.sh
uv run fastapi dev app/main.py
```

Run the frontend locally from the repository root:

```bash
bun install
bun run dev
```

## Environment Files

- Root `.env` configures Docker Compose and the backend.
- `frontend/.env` configures Vite, especially `VITE_API_URL`.
- Do not commit real `.env` files or secrets.

After changing environment values, restart the affected service.

## Transactional Email

Transactional mail (password recovery, the daily digest) goes out over the
Resend HTTP API — see `backend/app/services/resend_email.py`. The `SMTP_*`
settings are retained only so old `.env` files still parse; they drive
nothing.

**Nothing is delivered locally unless `RESEND_API_KEY` is set.** Sending is
gated on `settings.emails_enabled`, a computed property in
`backend/app/core/config.py` that is true only when both `RESEND_API_KEY` and
`EMAILS_FROM_EMAIL` are present. There is no flag to flip — set the two
environment variables in the root `.env` and it turns itself on. Without them,
sends are skipped. The API still reports success either way — `POST /password-recovery/{email}`
deliberately returns the same generic message whether the mail sent, failed, or
was never attempted, so the response can't be used to enumerate accounts. The
only signal is a warning in the backend log:

```bash
docker compose logs backend | grep -i resend
```

To get a working password-reset link locally without configuring Resend, render
the email directly as a superuser:

```
POST /api/v1/password-recovery-html-content/{email}
```

It returns the same HTML, with a freshly generated token. That's how the
Playwright suite obtains reset links (`frontend/tests/utils/recoveryEmail.ts`).

There is no local mail sandbox. A Mailcatcher container used to run alongside
the stack, but no mail has been sent to it since the move to Resend, so it was
removed rather than left to look useful.

## Linting And Tests

Frontend:

```bash
bun run lint
bun run test
bun run test:ui
cd frontend && bun run build
```

Backend:

```bash
cd backend
bash ./scripts/lint.sh
bash ./scripts/test.sh
```

The repo uses `prek` hooks through the backend dev dependencies. To install hooks:

```bash
cd backend
uv run prek install -f
```

## Generated Client

After backend OpenAPI changes:

```bash
bash ./scripts/generate-client.sh
```

Commit generated changes in `frontend/src/client` with the backend schema change that required them.
