"""Resend (https://resend.com) email sender.

Thin wrapper around the Resend HTTP API. We use Resend only for the
daily digest — password-reset transactional mail still flows through
``app.utils.send_email`` via the existing SMTP config. Splitting the
two avoids deliverability cross-contamination: digest is bulk, reset
is transactional, and ESPs reputation-score them differently.

Network calls are synchronous (httpx.Client) because the digest job
is a single background loop processing one user at a time. Per-call
timeout is short enough that a stuck Resend request can't hold the
worker for long, and any individual failure is logged and the loop
continues with the next user.
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


def send_email_via_resend(
    *,
    to: str,
    subject: str,
    html: str,
    text: str | None = None,
    reply_to: str | None = None,
    headers: dict[str, str] | None = None,
) -> ResendSendResult:
    """Send a single email through Resend.

    Returns a ``ResendSendResult`` rather than raising so the digest
    loop can record per-user outcomes and keep going. The only thing
    that aborts the loop is mis-configuration (no API key / no
    sender), which we surface up front via ``digest_email_enabled``.

    ``headers`` is exposed primarily so the caller can attach
    ``List-Unsubscribe`` and ``List-Unsubscribe-Post`` for one-click
    unsubscribe — Gmail/Yahoo bulk-sender requirements as of 2024.
    """
    if not settings.RESEND_API_KEY:
        return ResendSendResult(ok=False, error="RESEND_API_KEY not configured")

    from_email = settings.DIGEST_FROM_EMAIL or settings.EMAILS_FROM_EMAIL
    if not from_email:
        return ResendSendResult(
            ok=False, error="DIGEST_FROM_EMAIL / EMAILS_FROM_EMAIL not configured"
        )

    from_label = (
        f"{settings.EMAILS_FROM_NAME} <{from_email}>"
        if settings.EMAILS_FROM_NAME
        else str(from_email)
    )

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
    return ResendSendResult(ok=True, message_id=message_id)
