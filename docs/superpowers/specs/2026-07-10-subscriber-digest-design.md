# Subscriber digest send path (M8) — design

## Problem

`POST /subscriptions` collects anonymous emails into `digest_subscribers`,
and the landing-page `SubscribeBox` reports success — but nothing ever
reads that table. `run_digest_send` only walks the `User` table. Anonymous
subscribers are told they're subscribed and never receive anything.

This spec wires subscribers into a real send path.

## Decisions

- **Single opt-in.** Subscribing activates the address immediately — no
  confirmation step. (Reconsidered from an earlier double opt-in design.)
- **Immediate welcome send.** `POST /subscriptions` sends today's digest
  right away, best-effort, so a new subscriber gets value immediately; the
  daily scheduled job covers every following day.
- **Dedupe against users.** When a subscriber email also belongs to an
  active digest-enabled `User`, the scheduled subscriber send skips it —
  that person gets the personalized user digest instead of two morning
  emails.
- **Fixed UTC send hour.** Subscribers have no timezone, so the scheduled
  subscriber digest goes out once daily at a configured UTC hour (unlike the
  user digest, which fires at each user's local hour).
- **Generic content.** Subscribers get the anonymous digest
  (`build_digest(session, user_id=None)`), identical to what a logged-out
  visitor sees at `/digest/today-digest`.

## Data model

Add one nullable column to `DigestSubscriber` (Alembic migration,
`down_revision = c2d3e4f5a6b7`, no backfill):

- `last_digest_sent_at: datetime | None` — idempotency watermark, same role
  as `User.last_digest_sent_at`.

The existing `is_active` flag carries subscription state: `True` =
subscribed, `False` = unsubscribed. No confirmation column (single opt-in).

## Tokens (`services/subscriber_tokens.py`)

One signed JWT keyed by subscriber id, mirroring the existing `digest-unsub`
token in `digest_email.py` but with a distinct `type` claim
(`subscriber-unsub`) so it can never cross into the auth path:

- `make_subscriber_unsubscribe_token(subscriber_id)`
- `parse_subscriber_unsubscribe_token(token) -> UUID | None` — returns
  `None` on bad signature / wrong type / expired / malformed `sub`, so the
  endpoint renders a generic page without leaking the failure mode. TTL: 30
  days (same as the existing unsubscribe token).

## CRUD (`crud/subscriber.py`)

- `upsert_subscriber(session, email) -> (subscriber, created)` — create an
  active row or reactivate an existing one (unchanged behavior). Returns
  `created=True` only on first insert.
- `unsubscribe_subscriber(session, subscriber_id)` — set `is_active=False`;
  idempotent. Returns the row or None if missing.
- `get_sendable_subscribers(session)` — rows where `is_active = True`.
- `mark_subscriber_digest_sent(session, subscriber, now)` — stamp
  `last_digest_sent_at`.
- `get_active_digest_user_emails(session)` — set of lowercased emails of
  active, digest-enabled users, for the dedupe filter. (Lives in
  `crud/user.py`.)

## Endpoints (`api/routes/subscription.py`)

- `POST /subscriptions` — unchanged contract (201 for all inputs,
  `10/minute` rate limit). Upserts an active row, then best-effort sends
  today's anonymous digest to the address (build + Resend inline, wrapped so
  any failure is logged and never turns the 201 into an error, matching the
  guest-analytics best-effort pattern). A successful welcome send stamps
  `last_digest_sent_at`, so the same-day scheduled run skips the address (no
  double-send). The welcome send is a direct response to an explicit
  subscribe action and does **not** apply the user-dedupe filter — that
  filter only guards the recurring scheduled send. Still returns 201 whether
  the row was new or already existed, so enumeration stays closed.
- `GET /subscriptions/unsubscribe?token=…` and
  `POST /subscriptions/unsubscribe?token=…` — set `is_active=False`, render
  an HTML page. Idempotent. Always 200 (even on bad token) with an
  explanatory body, matching the existing digest unsubscribe page. The POST
  target satisfies RFC 8058 one-click unsubscribe from the
  `List-Unsubscribe` header on subscriber digests.

The HTML page reuses the `_render_page` shell pattern already in
`api/routes/digest.py`.

## Subscriber email (`services/subscriber_email.py`)

New small module owning:

- `send_subscriber_digest_email(session, subscriber)` — build the anonymous
  digest, and if it has content, render it for a bare email by calling the
  existing `digest_email._render_html` / `_render_text` with `full_name=None`
  and the subscriber's unsubscribe URL, then send via `send_email_via_resend`
  with `List-Unsubscribe` / `List-Unsubscribe-Post` headers. Returns the
  `ResendSendResult` (or an `ok=False` empty-digest result). Accepts an
  optional pre-built digest so the scheduled job can build once and reuse it
  across all subscribers.

`_render_html` / `_render_text` already take plain args (no `User`), so
there is no digest-rendering duplication. No new digest markup is needed.

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
   send (reusing the pre-built digest); on success stamp
   `last_digest_sent_at`. Per-subscriber failures are caught and logged; the
   loop never aborts midway.
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

- **Tokens**: unsubscribe round-trip; wrong type rejected; tampered/expired
  → None.
- **CRUD**: upsert creates active + `created=True`; re-subscribe reactivates
  + `created=False`; unsubscribe is idempotent; `get_sendable_subscribers`
  excludes unsubscribed rows.
- **Endpoints**: subscribe → 201 + welcome digest sent (mocked sender) + row
  active; subscribe with empty digest → 201 and no send; unsubscribe (GET and
  POST) deactivates; bad token → 200 generic page, no state change.
- **Send job**: sends only to active subscribers; skips emails that match an
  active digest-enabled user; idempotent within a UTC day; one subscriber's
  send failure doesn't abort the rest; empty digest → no sends;
  `digest_email_enabled` false → no-op.

All email sending is exercised against a mocked Resend client (no network),
following the existing `test_digest_email` / `test_digest` patterns.

## Out of scope

- Per-subscriber personalization (subscribers are anonymous).
- Subscriber timezones / local-hour delivery.
- Admin UI for the subscriber list.
- Double opt-in / confirmation flow (removed by decision).
