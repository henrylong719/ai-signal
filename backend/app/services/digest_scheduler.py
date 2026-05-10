"""Hourly job that sends each opted-in user their daily digest at local 6am.

Run loop sketch:

    for user in users where daily_digest_enabled:
        if not should_send_now(user, clock=now): continue
        send_digest_email(user)
        if ok: stamp last_digest_sent_at = now

Timezone handling lives in ``should_send_now`` so it is unit-testable
without DB/email setup. The scheduler entry point ``run_digest_send``
just walks the user table and dispatches.

Idempotency: once a user has ``last_digest_sent_at`` whose **local
calendar date** equals ``now``'s local calendar date, they are
skipped. This prevents duplicate sends if the hourly tick re-fires
(scheduler restart, container migration). Failures do not stamp, so a
transient Resend outage will retry on the next hour fire — but the
local-hour gate confines retries to a single 1-hour window per day,
which is the right tradeoff between deliverability and inbox spam.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime, timezone
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from sqlmodel import Session, select

from app.core.config import settings
from app.core.db import engine
from app.models import User
from app.services.digest_email import send_digest_email

logger = logging.getLogger(__name__)


def _resolve_zone(tz_name: str | None) -> ZoneInfo:
    """Return the user's tz, falling back to UTC.

    A bad tz string in the DB (older row, manual edit, or a legacy
    browser locale we no longer recognize) silently falls back to UTC
    rather than blocking the entire send loop.
    """
    if not tz_name:
        return ZoneInfo("UTC")
    try:
        return ZoneInfo(tz_name)
    except ZoneInfoNotFoundError:
        logger.warning("Unknown user timezone %r; falling back to UTC", tz_name)
        return ZoneInfo("UTC")


def should_send_now(
    user: User,
    *,
    now: datetime,
    target_hour: int | None = None,
) -> bool:
    """Decide whether a user should be sent the digest at this tick.

    True iff:
      - the user has opted in
      - their local-clock hour equals ``target_hour`` (default 8)
      - they have not been sent the digest yet on the current local
        calendar day

    Pure function over the user record + clock so tests can drive
    every branch without hitting Resend or the DB.
    """
    if not user.daily_digest_enabled:
        return False
    if now.tzinfo is None:
        # Defensive: tz-naive ``now`` would silently compare against
        # local-system time, which is exactly the bug we're avoiding.
        raise ValueError("now must be timezone-aware")

    target = target_hour if target_hour is not None else settings.DIGEST_SEND_LOCAL_HOUR
    zone = _resolve_zone(user.timezone)
    now_local = now.astimezone(zone)
    if now_local.hour != target:
        return False

    last = user.last_digest_sent_at
    if last is None:
        return True
    if last.tzinfo is None:
        # Postgres timestamptz comes back tz-aware, but if a test
        # constructs a naive datetime treat it as UTC.
        last = last.replace(tzinfo=timezone.utc)
    last_local_date = last.astimezone(zone).date()
    return last_local_date != now_local.date()


# --- Send loop --------------------------------------------------------------


@dataclass(frozen=True)
class SendLoopOutcome:
    """Counters surfaced for observability and tests."""

    candidates: int
    sent: int
    skipped: int
    failed: int


def _candidate_users(session: Session) -> list[User]:
    """Users opted into the digest.

    The local-hour and idempotency checks happen in ``should_send_now``
    so this stays a single index-friendly DB query rather than a join
    on a derived expression.
    """
    statement = select(User).where(User.daily_digest_enabled == True)  # noqa: E712
    return list(session.exec(statement).all())


def run_digest_send(*, now: datetime | None = None) -> SendLoopOutcome:
    """Iterate opted-in users and send the digest where due.

    Opens its own DB session so the APScheduler-owned loop doesn't
    have to. Per-user errors are caught and logged; the loop never
    aborts midway through the user list.
    """
    if not settings.digest_email_enabled:
        logger.info(
            "Digest email skipped: RESEND_API_KEY / DIGEST_FROM_EMAIL not configured",
        )
        return SendLoopOutcome(candidates=0, sent=0, skipped=0, failed=0)

    clock = now or datetime.now(timezone.utc)
    sent = skipped = failed = 0

    with Session(engine) as session:
        users = _candidate_users(session)
        for user in users:
            try:
                if not should_send_now(user, now=clock):
                    skipped += 1
                    continue
                result = send_digest_email(session=session, user=user)
                if result.ok:
                    # Stamp using the loop's clock (not wall-clock) so
                    # tests that pass an explicit ``now`` get a
                    # consistent watermark; in production they're the
                    # same value.
                    user.last_digest_sent_at = clock
                    session.add(user)
                    session.commit()
                    sent += 1
                else:
                    # ``ok=False`` covers both empty-digest skips and
                    # Resend errors. We log either way; don't stamp
                    # last_sent so a real failure retries next hour
                    # within the same local-hour window.
                    logger.info(
                        "Digest not sent to user=%s: %s",
                        user.id,
                        result.error,
                    )
                    failed += 1
            except Exception:
                # The send loop must keep moving — one user's failure
                # cannot abort the run.
                session.rollback()
                logger.exception(
                    "Unhandled digest-send error for user=%s; continuing",
                    user.id,
                )
                failed += 1

        return SendLoopOutcome(
            candidates=len(users),
            sent=sent,
            skipped=skipped,
            failed=failed,
        )
