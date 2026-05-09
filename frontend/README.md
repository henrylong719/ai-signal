# AI Signal Frontend

The frontend is a React 19, TypeScript, Vite, TanStack Router, TanStack Query, Tailwind CSS, and Radix UI app.

## Requirements

- [Bun](https://bun.sh/)
- A running AI Signal backend at the URL in `VITE_API_URL`

## Local Setup

From the repository root:

```bash
bun install
cp frontend/.env.example frontend/.env
bun run dev
```

Open `http://localhost:5173`.

## Environment

```env
VITE_API_URL=http://localhost:8000
```

For deployed builds, set `VITE_API_URL` to the public backend API origin, such as `https://api.example.com`.

## Commands

From the repository root:

```bash
bun run dev
bun run lint
bun run test
bun run test:ui
```

From `frontend/`:

```bash
bun run build
bun run preview
bun run generate-client
```

## Generated API Client

The generated OpenAPI client lives in `frontend/src/client`.

Prefer the root script:

```bash
bash ./scripts/generate-client.sh
```

Run it after backend schema changes, after adding or changing endpoints, and before frontend code depends on new request/response types. The script exports the backend OpenAPI schema, moves it to `frontend/openapi.json`, runs `bun run --filter frontend generate-client`, then runs the frontend lint command.

If you already have a fresh `frontend/openapi.json`, the lower-level command is:

```bash
cd frontend
bun run generate-client
```

## Code Structure

- `src/client` contains generated API client code.
- `src/components` contains reusable UI and feature components.
- `src/hooks` contains feed, auth, source, and personalization hooks.
- `src/routes` contains TanStack Router file routes.
- `tests` contains Playwright tests and helpers.

## End-to-End Tests

Playwright tests expect the app stack or required services to be available:

```bash
docker compose up -d --wait backend
bun run test
```

Use UI mode while developing tests:

```bash
bun run test:ui
```
