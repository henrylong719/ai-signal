"""Daily job that sends the generic digest to anonymous subscribers.

Sibling of ``digest_scheduler.run_digest_send`` (which handles registered
users at their local hour). Subscribers have no timezone, so this loop
fires once per day at a fixed UTC hour and sends the same anonymous digest
to every active subscriber.

Run loop sketch:

    if not digest_email_enabled: return
    digest = build_digest(user_id=None)          # built once, reused
    if digest is empty: return
    user_emails = active digest-enabled user emails   # dedupe set
    for sub in active subscribers:
        if sub.email in user_emails: skip           # they get the user digest
        if already sent today (UTC): skip
        send(digest); on ok stamp last_digest_sent_at

Idempotency: a subscriber whose ``last_digest_sent_at`` lands on the
current UTC calendar day is skipped, so a re-fired tick — or the welcome
send earlier the same day — can't deliver twice. Per-subscriber failures
are caught and logged; the loop never aborts midway.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime, timezone

from sqlmodel import Session

from app.core.config import settings
from app.core.db import engine
from app.services.digest import build_digest
from app.services.digest_email import _has_content
from app.services.subscriber_email import (
    already_sent_on_utc_day,
    send_subscriber_digest_email,
)

logger = logging.getLogger(__name__)

__all__ = ["SubscriberSendOutcome", "build_digest", "run_subscriber_digest_send"]


@dataclass(frozen=True)
class SubscriberSendOutcome:
    """Counters surfaced for observability and tests."""

    candidates: int
    sent: int
    skipped: int
    failed: int


def run_subscriber_digest_send(*, now: datetime | None = None) -> SubscriberSendOutcome:
    """Send the generic digest to every eligible subscriber.

    Opens its own DB session so the APScheduler-owned loop doesn't have to.
    """
    if not settings.digest_email_enabled:
        logger.info(
            "Subscriber digest skipped: RESEND_API_KEY / DIGEST_FROM_EMAIL "
            "not configured",
        )
        return SubscriberSendOutcome(candidates=0, sent=0, skipped=0, failed=0)

    # Local import mirrors the rest of the services layer (see
    # embeddings.py): keeps the crud→services import graph acyclic.
    from app import crud

    clock = now or datetime.now(timezone.utc)
    sent = skipped = failed = 0

    with Session(engine) as session:
        # Build the anonymous digest once and reuse it for every subscriber.
        digest = build_digest(session=session, user_id=None)
        if not _has_content(digest):
            logger.info("Subscriber digest is empty; skipping run")
            return SubscriberSendOutcome(candidates=0, sent=0, skipped=0, failed=0)

        user_emails = crud.get_active_digest_user_emails(session=session)
        subscribers = list(crud.get_sendable_subscribers(session=session))

        for subscriber in subscribers:
            try:
                if subscriber.email.lower() in user_emails:
                    # They receive the personalized user digest instead.
                    skipped += 1
                    continue
                if already_sent_on_utc_day(subscriber, now=clock):
                    skipped += 1
                    continue
                result = send_subscriber_digest_email(
                    session=session, subscriber=subscriber, digest=digest
                )
                if result.ok:
                    crud.mark_subscriber_digest_sent(
                        session=session, subscriber=subscriber, now=clock
                    )
                    sent += 1
                else:
                    logger.info(
                        "Subscriber digest not sent to %s: %s",
                        subscriber.id,
                        result.error,
                    )
                    failed += 1
            except Exception:
                session.rollback()
                logger.exception(
                    "Unhandled subscriber-digest error for %s; continuing",
                    subscriber.id,
                )
                failed += 1

        return SubscriberSendOutcome(
            candidates=len(subscribers),
            sent=sent,
            skipped=skipped,
            failed=failed,
        )
