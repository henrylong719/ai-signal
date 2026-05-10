# AI Signal Launch Checklist

Use this as a production-readiness pass before opening AI Signal to public traffic. Every item below should be checked off and dated by the engineer running the launch.

The production domain is **`https://aisignal.now`**. Anywhere this checklist references "production domain" it means that exact origin (with HTTPS).

## 1. Domain, branding, and SEO

- [ ] DNS for `aisignal.now` resolves to the production deployment with a valid TLS certificate.
- [ ] `frontend/index.html` declares the right title, description, theme-color, favicon, and Open Graph / Twitter image (`/og-image.png`, 1200×630, on-brand).
- [ ] `frontend/public/robots.txt` allows the public surface and disallows `/admin*`, `/settings*`, `/personalization`, `/saved-articles`, and the auth routes. `Sitemap:` line points at the production domain.
- [ ] `frontend/public/sitemap.xml` references `https://aisignal.now` and lists every public route (home, about, sources directory, sources policy, privacy, terms, cookies, accessibility, contact). Authenticated-only routes are absent.
- [ ] JSON-LD `WebSite` + `Organization` in `index.html` references the production URL (already wired — verify the SearchAction `urlTemplate` matches `https://aisignal.now/search-feed/{search_term_string}`).
- [ ] Per-page OG / canonical tags are emitted (helper in `frontend/src/lib/meta.ts`). Spot-check by sharing `/about`, `/today-digest`, and `/all-article-sources` URLs and confirming the previews are page-specific, not the home fallback.
- [ ] Test share preview at https://www.opengraph.xyz/ or with the WhatsApp / Slack link unfurl.

## 2. Legal, contact, and brand mailbox

- [ ] `hello@aisignal.now` (the value of `CONTACT_EMAIL` in `frontend/src/lib/legal.ts`) is a real, monitored mailbox. SPF / DKIM / DMARC records are in place for outbound mail from this domain.
- [ ] `LEGAL_LAST_UPDATED` reflects the actual revision date of the published policy text. Do not bump on every commit.
- [ ] Privacy, Terms, Cookies, Accessibility, Sources Policy, About, and Contact pages are reachable from the global footer on every route.
- [ ] All `mailto:` links (Contact page, Accessibility, Sources Policy, etc.) resolve to the brand mailbox above.

## 3. Environment configuration (production `.env`)

Pin every value below explicitly — relying on a default is fine locally, but in prod we want intent visible at a glance.

- [ ] **Secrets** — `SECRET_KEY`, `FIRST_SUPERUSER_PASSWORD`, `POSTGRES_PASSWORD` are strong, unique, and not the `changethis` placeholder.
- [ ] **CORS / origins** — `BACKEND_CORS_ORIGINS` and `FRONTEND_HOST` reference `https://aisignal.now`. No localhost values.
- [ ] **Frontend** — `VITE_API_URL` in the production frontend build points at the public API origin.
- [ ] **Rate limiting** — `RATE_LIMIT_STORAGE_URI` set to a shared backend (e.g. `redis://redis:6379`) for any deployment running more than one worker. Without this, each worker hands out the full per-bucket allowance, multiplying the configured limit by the worker count.
- [ ] **Ingestion scheduler** — `INGEST_SCHEDULER_ENABLED` explicitly `true` or `false`. The resolved default is enabled in non-local environments, but pinning it makes the deployed behavior survive future default changes.
- [ ] **Sentry** — `SENTRY_DSN` set if observability is desired (no-op if blank, only initialized outside `local`).

## 4. Database and migrations

- [ ] `uv run alembic upgrade head` has been run against the production database. The most recent revisions to confirm:
  - `5d6e7f8a9b0c` — digest subscribers table
  - `6e7f8a9b0c1d` — digest + onboarding fields on `user` (`timezone`, `daily_digest_enabled`, `last_digest_sent_at`, `onboarded_at`)
- [ ] pgvector extension is installed in the production database and the article embedding column exists.
- [ ] At least one supervised ingestion run has completed via the superuser endpoint, and the ingest-runs admin page shows green status.

## 5. Transactional email (password reset + new account)

These flow through the existing SMTP path in `app/utils.py`, separate from the digest pipeline.

- [ ] `SMTP_HOST`, `SMTP_PORT`, `SMTP_USER`, `SMTP_PASSWORD`, `EMAILS_FROM_EMAIL`, `EMAILS_FROM_NAME` are populated.
- [ ] Password reset flow tested end-to-end: request reset → email lands → click link → set new password.
- [ ] Sender domain has SPF / DKIM aligned (so password resets aren't quarantined by recipient inbox providers).

## 6. Daily digest email (Resend)

The digest scheduler short-circuits if credentials are missing, so missing config is silent — verify it's wired before launch.

- [ ] **Resend account** — domain `aisignal.now` (or your chosen sender domain) is verified in Resend with DNS records propagated.
- [ ] **`RESEND_API_KEY`** set in production `.env`.
- [ ] **`DIGEST_FROM_EMAIL`** set to a verified sender on the Resend domain. Falls back to `EMAILS_FROM_EMAIL` if unset; explicit value preferred so digest reputation is tracked separately from transactional mail.
- [ ] **`DIGEST_SEND_LOCAL_HOUR`** is sensible (default `8`).
- [ ] **Sanity send** — create a test user, set `daily_digest_enabled=true` and `timezone` to a zone where the local hour will hit `DIGEST_SEND_LOCAL_HOUR` shortly. Wait for the next top-of-hour fire and confirm:
  - The email arrives at the inbox.
  - Subject reads `Your AI Signal — <date>`.
  - Article links go through `/api/v1/articles/{id}/go` (clicks should record).
  - The "Manage preferences" link lands on `/settings`.
  - The "Unsubscribe" link toggles `daily_digest_enabled` to false and renders the success page.
- [ ] **One-click unsubscribe** — Gmail / Yahoo bulk-sender headers are emitted; verify by opening the email's source and confirming `List-Unsubscribe` and `List-Unsubscribe-Post` headers are present.
- [ ] **Idempotency** — a second hourly tick within the same local-day does not re-send (`last_digest_sent_at` watermark gates it).

## 7. First-run onboarding flow

- [ ] Sign up a fresh test account. The `OnboardingDialog` opens on first authenticated visit.
- [ ] All four steps render correctly: welcome → topics → sources → preview / digest opt-in.
- [ ] Browser timezone is detected (`Intl.DateTimeFormat().resolvedOptions().timeZone`) and surfaced on the final step.
- [ ] Finishing the flow:
  - Persists topics + sources via `PUT /users/me/interests`.
  - Sets `timezone`, `daily_digest_enabled`, and `onboarded_at` via `PUT /users/me/onboarding`.
  - Closes the modal.
- [ ] Closing without finishing (X / `Skip for now` / click-outside) still marks `onboarded_at` and does **not** re-open on the next session.
- [ ] The `/settings` page exposes the "Daily Digest" section; toggling and saving updates the user record.

## 8. Security and admin

- [ ] All `/admin/*` routes return 403 for non-superusers and 401 for anonymous requests.
- [ ] Ingestion endpoint (`POST /api/v1/ingest`) and admin embedding backfill require superuser.
- [ ] Outbound article redirect (`GET /api/v1/articles/{id}/go`) is open-redirect-safe — destination URL is read from the DB, scheme is allow-listed, and no query parameter steers the redirect.
- [ ] Unsubscribe token (`/api/v1/digest/unsubscribe?token=…`) cannot be replayed as an access token (distinct `type` claim, verified in tests).
- [ ] Cookies (`access_token`, `refresh_token`) are HttpOnly, Secure, SameSite=Lax in production. Refresh cookie is path-scoped to `/api/v1/login/refresh`.

## 9. Performance and accessibility

- [ ] Article images use `loading="lazy"` and `decoding="async"` (already wired in `ArticleCard`).
- [ ] `prefers-reduced-motion: reduce` is honored — verify by enabling the OS-level reduced-motion setting and confirming animations / smooth-scroll are skipped.
- [ ] Skip-to-content link in `AppShell` is the first focusable element on every page.
- [ ] Lighthouse audit on `/` and `/about` returns Performance ≥ 80, Accessibility ≥ 95, Best Practices ≥ 90, SEO ≥ 95.

## 10. Deployment smoke test

- [ ] Backend `/api/v1/utils/health-check/` returns 200.
- [ ] OpenAPI docs load at `/docs` (or are intentionally disabled in prod — confirm the chosen state).
- [ ] Frontend build (`bun run build` from `frontend/`) succeeds and references the production `VITE_API_URL`.
- [ ] Generated API client is current — run `bash ./scripts/generate-client.sh` and confirm the diff is clean. Specifically, `UsersService.completeOnboarding` and `UsersService.updateDigestPreferences` exist on the SDK.
- [ ] Auth flows (sign up, sign in, refresh, sign out, password reset) work end-to-end against the production origin.
- [ ] OAuth providers (Google, GitHub, Facebook) — for each enabled provider: redirect URI in the provider console matches `https://aisignal.now/api/v1/login/<provider>/callback`, and a test sign-in completes.
- [ ] Public-route smoke: `/`, `/about`, `/all-article-sources`, `/article-sources/<source>`, `/category-feed/<cat>`, `/search-feed/<q>`, `/today-digest` all render content (or the appropriate empty state) without console errors.
- [ ] Authed-route smoke: `/settings`, `/personalization`, `/saved-articles`, For You + Following tabs all work.

## 11. Day-zero monitoring

- [ ] Sentry is receiving events from a deliberately-thrown error (or absence is intentional).
- [ ] Logs from the FastAPI process are aggregated somewhere queryable.
- [ ] APScheduler job logs (ingestion + hourly digest) show up in the log stream after the first ticks.
- [ ] DB connection count / Postgres CPU has a baseline graph.
