"""Low-level Resend (https://resend.com) HTTP client.

All AI Signal app email — transactional (password reset, new account,
test email) and bulk (daily digest) — is delivered through this
single Resend wrapper. The unified service in ``app.services.email``
is the high-level surface that callers should use; this module only
exists to keep the HTTP/transport detail in one place so the rest of
the app never builds a Resend payload by hand.

Network calls are synchronous (``httpx.post``) because every caller
today is either a request-thread (transactional) or a single
background loop processing one user at a time (digest). Per-call
timeout is short enough that a stuck Resend request can't hold the
caller for long, and any individual failure is logged and returned
as a structured ``ResendSendResult`` so the caller can decide
whether to abort, retry, or continue.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass

import httpx

from app.core.config import settings

logger = logging.getLogger(__name__)

_RESEND_ENDPOINT = "https://api.resend.com/emails"
_RESEND_TIMEOUT_SECONDS = 10.0


@dataclass(frozen=True)
class ResendSendResult:
    """Outcome of a single send.

    ``message_id`` is the id Resend assigns; useful for ops correlation
    if a delivery is later questioned. ``ok`` is the only field callers
    typically branch on — ``error`` carries a short string for logs.
    """

    ok: bool
    message_id: str | None = None
    error: str | None = None


def _resolve_from_label(from_email: str | None) -> str | None:
    """Build the ``From:`` header Resend wants.

    Resolution order:

      1. Explicit ``from_email`` arg (caller knows what it wants — used
         by the digest sender to override with ``DIGEST_FROM_EMAIL``
         so transactional and bulk traffic ride different senders).
      2. ``EMAILS_FROM_EMAIL`` from settings (the default transactional
         identity for the whole app).

    Returns ``None`` when no sender is available so the caller can
    surface a clear configuration error instead of letting Resend
    bounce the request.
    """
    sender = from_email or settings.EMAILS_FROM_EMAIL
    if not sender:
        return None
    sender = str(sender)
    # Allow callers to pass a pre-formatted ``Name <addr>`` string
    # (e.g. when a settings value already includes the display name).
    if "<" in sender and ">" in sender:
        return sender
    if settings.EMAILS_FROM_NAME:
        return f"{settings.EMAILS_FROM_NAME} <{sender}>"
    return sender


def send_email_via_resend(
    *,
    to: str,
    subject: str,
    html: str,
    text: str | None = None,
    from_email: str | None = None,
    reply_to: str | None = None,
    headers: dict[str, str] | None = None,
) -> ResendSendResult:
    """Send a single email through Resend.

    Returns a ``ResendSendResult`` rather than raising so callers
    (the password-recovery handler, the digest send loop) can record
    per-call outcomes and decide what to do without a try/except
    wrapper. The only thing that aborts is mis-configuration (no API
    key / no sender), which is surfaced via ``ok=False`` + ``error``.

    ``headers`` is exposed primarily so the digest sender can attach
    ``List-Unsubscribe`` and ``List-Unsubscribe-Post`` for one-click
    unsubscribe — Gmail/Yahoo bulk-sender requirements as of 2024.
    """
    if not settings.RESEND_API_KEY:
        logger.warning(
            "Resend send aborted: RESEND_API_KEY is not configured (to=%s)",
            to,
        )
        return ResendSendResult(ok=False, error="RESEND_API_KEY not configured")

    from_label = _resolve_from_label(from_email)
    if not from_label:
        logger.warning(
            "Resend send aborted: EMAILS_FROM_EMAIL is not configured (to=%s)",
            to,
        )
        return ResendSendResult(ok=False, error="EMAILS_FROM_EMAIL not configured")

    payload: dict[str, object] = {
        "from": from_label,
        "to": [to],
        "subject": subject,
        "html": html,
    }
    if text:
        payload["text"] = text
    if reply_to:
        payload["reply_to"] = reply_to
    if headers:
        payload["headers"] = headers

    try:
        response = httpx.post(
            _RESEND_ENDPOINT,
            headers={
                "Authorization": f"Bearer {settings.RESEND_API_KEY}",
                "Content-Type": "application/json",
            },
            json=payload,
            timeout=_RESEND_TIMEOUT_SECONDS,
        )
    except httpx.HTTPError as exc:
        logger.warning("Resend network error sending to %s: %s", to, exc)
        return ResendSendResult(ok=False, error=f"network: {exc}")

    if response.status_code >= 400:
        # Truncate the body — Resend can return verbose error JSON and
        # we don't want to dump full payloads into the log line.
        body = response.text[:300]
        logger.warning(
            "Resend returned %s sending to %s: %s",
            response.status_code,
            to,
            body,
        )
        return ResendSendResult(ok=False, error=f"http {response.status_code}: {body}")

    try:
        data = response.json()
    except ValueError:
        return ResendSendResult(ok=True, message_id=None)
    message_id = data.get("id") if isinstance(data, dict) else None
    logger.info("Resend accepted email to=%s message_id=%s", to, message_id)
    return ResendSendResult(ok=True, message_id=message_id)
