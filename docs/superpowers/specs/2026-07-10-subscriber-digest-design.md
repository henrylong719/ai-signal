# Subscriber digest send path (M8) — design

## Problem

`POST /subscriptions` collects anonymous emails into `digest_subscribers`,
and the landing-page `SubscribeBox` reports success — but nothing ever
reads that table. `run_digest_send` only walks the `User` table. Anonymous
subscribers are told they're subscribed and never receive anything. The
endpoint also has no confirmation step, so anyone can subscribe someone
else's address.

This spec wires subscribers into a real send path with double opt-in and
unsubscribe.

## Decisions

- **Double opt-in.** Subscribing creates a *pending* row and sends a
  confirmation email; only confirmed subscribers receive the digest. Closes
  the "subscribe a stranger" abuse vector and is the deliverability norm.
- **Dedupe against users.** When a subscriber email also belongs to an
  active digest-enabled `User`, the subscriber send skips it — that person
  gets the personalized user digest instead of two morning emails.
- **Fixed UTC send hour.** Subscribers have no timezone, so the subscriber
  digest goes out once daily at a configured UTC hour (unlike the user
  digest, which fires at each user's local hour).
- **Generic content.** Subscribers get the anonymous digest
  (`build_digest(session, user_id=None)`), identical to what a logged-out
  visitor sees at `/digest/today-digest`.

## Data model

Add two nullable columns to `DigestSubscriber` (Alembic migration,
`down_revision = c2d3e4f5a6b7`, no backfill — no real subscribers exist):

- `confirmed_at: datetime | None` — `NULL` = pending (confirmation email
  sent, not yet clicked); non-null = confirmed.
- `last_digest_sent_at: datetime | None` — idempotency watermark, same role
  as `User.last_digest_sent_at`.

States: **pending** (`confirmed_at IS NULL, is_active = True`),
**confirmed** (`confirmed_at` set, `is_active = True`), **unsubscribed**
(`is_active = False`).

## Tokens (`services/subscriber_tokens.py`)

Two signed JWTs keyed by subscriber id, mirroring the existing
`digest-unsub` token in `digest_email.py`, each with a distinct `type`
claim so none can cross into the auth path or into each other:

- `make_subscriber_confirm_token(subscriber_id)` — type `subscriber-confirm`.
- `make_subscriber_unsubscribe_token(subscriber_id)` — type `subscriber-unsub`.
- `parse_subscriber_confirm_token(token) -> UUID | None`
- `parse_subscriber_unsubscribe_token(token) -> UUID | None`

Both parse functions return `None` on bad signature / wrong type / expired /
malformed `sub`, so callers render a generic page without leaking the
failure mode. TTL: 30 days (same as the existing unsubscribe token).

## CRUD (`crud/subscriber.py`)

- `upsert_subscriber(session, email) -> (subscriber, created)` — create a
  pending row (`confirmed_at=None`) or return the existing one. Never
  reactivates or re-confirms; confirmation state changes go through
  `confirm_subscriber`.
- `confirm_subscriber(session, subscriber_id)` — set `confirmed_at` if not
  already set; idempotent. Returns the row or None if missing.
- `unsubscribe_subscriber(session, subscriber_id)` — set `is_active=False`;
  idempotent. Returns the row or None.
- `get_sendable_subscribers(session)` — rows where `is_active = True AND
  confirmed_at IS NOT NULL`.
- `mark_subscriber_digest_sent(session, subscriber, now)` — stamp
  `last_digest_sent_at`.
- `get_active_digest_user_emails(session)` — set of lowercased emails of
  active, digest-enabled users, for the dedupe filter. (Lives in
  `crud/user.py`.)

## Endpoints (`api/routes/subscription.py`)

- `POST /subscriptions` — unchanged contract (201 for all inputs,
  `10/minute` rate limit). Upserts a pending row; if the row is not yet
  confirmed, sends a confirmation email with a `subscriber-confirm` link.
  If already confirmed, no email is sent (still 201) — so a confirmed
  address can't be re-mailed via this endpoint and enumeration stays closed.
- `GET /subscriptions/confirm?token=…` — validate token, set `confirmed_at`,
  render an HTML confirmation page. Idempotent. Always 200 (even on bad
  token) with an explanatory body, matching the existing unsubscribe page.
- `GET /subscriptions/unsubscribe?token=…` and
  `POST /subscriptions/unsubscribe?token=…` — set `is_active=False`, render
  a page. Idempotent. The POST target satisfies RFC 8058 one-click
  unsubscribe from the `List-Unsubscribe` header on subscriber digests.

The HTML pages reuse the `_render_page` shell pattern already in
`api/routes/digest.py` (extracted/shared if practical, otherwise a small
local template).

## Confirmation email (`services/subscriber_email.py`)

New small module owning:

- `send_subscriber_confirmation_email(session, subscriber)` — minimal inline
  HTML with a single "Confirm subscription" CTA pointing at
  `/subscriptions/confirm?token=…`, sent via `send_email_via_resend` from
  the digest sender identity.
- `send_subscriber_digest_email(digest, subscriber)` — renders the anonymous
  digest for a bare email by calling the existing
  `digest_email._render_html` / `_render_text` with `full_name=None` and the
  subscriber's unsubscribe URL, then sends with `List-Unsubscribe` /
  `List-Unsubscribe-Post` headers.

`_render_html` / `_render_text` already take plain args (no `User`), so
there is no digest-rendering duplication — only the confirmation email is
new markup.

## Send job (`services/subscriber_digest.py`)

`run_subscriber_digest_send(now=None) -> SubscriberSendOutcome`:

1. Return zeros if `settings.digest_email_enabled` is false.
2. Build the anonymous digest **once**; if it has no content, skip the run
   (sending an empty digest is worse than skipping — same rule as the user
   path).
3. Load `get_active_digest_user_emails` (dedupe set) and
   `get_sendable_subscribers`.
4. Per subscriber: skip if the email is in the user set; skip if
   `last_digest_sent_at` is already today (UTC calendar day); else render and
   send; on success stamp `last_digest_sent_at`. Per-subscriber failures are
   caught and logged; the loop never aborts midway.
5. Return counters `(candidates, sent, skipped, failed)`, mirroring
   `SendLoopOutcome`.

## Scheduling + config

- New setting `SUBSCRIBER_DIGEST_SEND_HOUR_UTC: int = 6`.
- Register a daily cron job in `services/scheduler.py` next to the user
  digest job, `hour=SUBSCRIBER_DIGEST_SEND_HOUR_UTC, minute=0`, UTC,
  `coalesce=True, max_instances=1`, `misfire_grace_time=3600`. The job
  short-circuits internally when `digest_email_enabled` is false, matching
  the user digest job.

## Testing

- **Tokens**: round-trip confirm/unsub; wrong type rejected; tampered/expired
  → None; a `subscriber-confirm` token rejected by the unsubscribe parser
  and vice versa.
- **CRUD**: upsert creates pending; confirm is idempotent; unsubscribe is
  idempotent; `get_sendable_subscribers` excludes pending and unsubscribed.
- **Endpoints**: subscribe → 201 + confirmation email sent (mocked sender) +
  row pending; confirm link activates; already-confirmed subscribe sends no
  second email; unsubscribe (GET and POST) deactivates; bad tokens → 200
  generic page, no state change.
- **Send job**: sends only to confirmed active subscribers; skips emails
  that match an active digest-enabled user; idempotent within a UTC day;
  one subscriber's send failure doesn't abort the rest; empty digest →
  no sends; `digest_email_enabled` false → no-op.

All email sending is exercised against a mocked Resend client (no network),
following the existing `test_digest_email` / `test_digest` patterns.

## Out of scope

- Per-subscriber personalization (subscribers are anonymous).
- Subscriber timezones / local-hour delivery.
- Admin UI for the subscriber list.
- Migrating existing `is_active=True` rows to confirmed (there are none).
