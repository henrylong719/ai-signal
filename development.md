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
- Mailcatcher: <http://localhost:1080>

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

## Mailcatcher

Local Docker Compose configures the backend to send email to Mailcatcher. View captured messages at <http://localhost:1080>.

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
