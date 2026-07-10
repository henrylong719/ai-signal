"""Digest email delivery for anonymous subscribers.

Subscribers get the *generic* digest (``build_digest(user_id=None)``) —
the same content a logged-out visitor sees at ``/digest/today-digest``.
Rendering reuses the user-digest email shell in ``digest_email`` verbatim
(those helpers take plain args, not a ``User``), so the only thing that
differs is the unsubscribe link: it carries a ``subscriber-unsub`` token
keyed by ``DigestSubscriber.id`` instead of the user token.

The one-time welcome send (from ``POST /subscriptions``) and the daily
scheduled send both go through ``send_subscriber_digest_email``. The
scheduled job builds the digest once and passes it in via ``digest=`` so
a run to N subscribers does one build, not N.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone

from sqlmodel import Session

from app.core.config import settings
from app.models.subscriber import DigestSubscriber
from app.services.digest import DigestPublic, build_digest
from app.services.digest_email import (
    _backend_url,
    _format_date,
    _frontend_url,
    _has_content,
    _render_html,
    _render_text,
)
from app.services.resend_email import ResendSendResult, send_email_via_resend
from app.services.subscriber_tokens import make_subscriber_unsubscribe_token

logger = logging.getLogger(__name__)

__all__ = [
    "build_digest",
    "already_sent_on_utc_day",
    "send_subscriber_digest_email",
]


def already_sent_on_utc_day(subscriber: DigestSubscriber, *, now: datetime) -> bool:
    """True if this subscriber was already sent a digest on ``now``'s UTC
    calendar day. Shared idempotency guard for the welcome send and the
    scheduled loop so neither double-delivers within a day."""
    last = subscriber.last_digest_sent_at
    if last is None:
        return False
    if last.tzinfo is None:
        last = last.replace(tzinfo=timezone.utc)
    return last.astimezone(timezone.utc).date() == now.astimezone(timezone.utc).date()


def _subscriber_unsubscribe_url(subscriber: DigestSubscriber) -> str:
    token = make_subscriber_unsubscribe_token(subscriber.id)
    return _backend_url("/subscriptions/unsubscribe", {"token": token})


def send_subscriber_digest_email(
    *,
    session: Session,
    subscriber: DigestSubscriber,
    digest: DigestPublic | None = None,
) -> ResendSendResult:
    """Render and send the generic digest to one subscriber.

    Builds the anonymous digest when ``digest`` is not supplied. Returns an
    ``ok=False`` result (without sending) when the digest is empty — an
    empty email is worse than none, same rule as the user path.
    """
    if digest is None:
        digest = build_digest(session=session, user_id=None)
    if not _has_content(digest):
        logger.info("Subscriber digest is empty; skipping send to %s", subscriber.id)
        return ResendSendResult(ok=False, error="empty digest")

    unsubscribe_url = _subscriber_unsubscribe_url(subscriber)
    # Anonymous subscribers have no account settings page; point "Manage
    # preferences" at the public digest page so the link never dead-ends at
    # a login wall. Unsubscribe is the load-bearing footer control.
    home_url = _frontend_url("/digest")

    html_body = _render_html(
        digest=digest,
        full_name=None,
        unsubscribe_url=unsubscribe_url,
        settings_url=home_url,
        home_url=home_url,
    )
    text_body = _render_text(
        digest=digest,
        full_name=None,
        unsubscribe_url=unsubscribe_url,
        home_url=home_url,
    )

    subject = f"Today’s Signal — {_format_date(digest.generated_at)}"
    digest_from = (
        str(settings.DIGEST_FROM_EMAIL)
        if settings.DIGEST_FROM_EMAIL
        else (str(settings.EMAILS_FROM_EMAIL) if settings.EMAILS_FROM_EMAIL else None)
    )

    return send_email_via_resend(
        to=subscriber.email,
        subject=subject,
        html=html_body,
        text=text_body,
        from_email=digest_from,
        headers={
            "List-Unsubscribe": f"<{unsubscribe_url}>",
            "List-Unsubscribe-Post": "List-Unsubscribe=One-Click",
        },
    )
