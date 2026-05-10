"""Unified app email service — Resend for everything.

This is the single entrypoint app code should use to send mail.
Internally it dispatches to ``app.services.resend_email`` (the
HTTP wrapper for the Resend API). Splitting the high-level intent
("send a password reset to this user") from the transport keeps
callers free of provider details and gives us one place to add
cross-cutting concerns later (rate limits, suppressions, retries).

Provider history: AI Signal previously used the ``emails`` Python
package over SMTP for transactional mail and Resend only for the
daily digest. Maintaining two providers meant two deliverability
profiles, two sets of credentials, and two failure modes. The
``aisignal.now`` domain is verified in Resend, so everything now
flows through one provider.

Public API:

  - :func:`send_email` — generic transactional send (subject + html).
  - :func:`send_password_reset_email` — wraps the existing
    Jinja-based reset template.
  - :func:`send_new_account_email` — admin-created account welcome.
  - :func:`send_test_email` — used by the admin "send test email"
    endpoint to confirm the Resend wiring works end-to-end.
  - :func:`send_digest_email` — re-exported from
    :mod:`app.services.digest_email` so callers have a single import.

All senders return :class:`ResendSendResult` (``ok`` / ``message_id``
/ ``error``) instead of raising. Callers that need to gate side
effects on send success can branch on ``ok``; callers that just
want best-effort delivery (password recovery, where we always
return the same generic response to avoid email enumeration) can
ignore the result.
"""

from __future__ import annotations

import logging

from app.services.digest_email import send_digest_email
from app.services.resend_email import ResendSendResult, send_email_via_resend
from app.utils import (
    generate_new_account_email,
    generate_reset_password_email,
    generate_test_email,
)

logger = logging.getLogger(__name__)


def send_email(
    *,
    to: str,
    subject: str,
    html: str,
    text: str | None = None,
    from_email: str | None = None,
    reply_to: str | None = None,
    headers: dict[str, str] | None = None,
) -> ResendSendResult:
    """Send a transactional email via Resend.

    Thin pass-through to :func:`send_email_via_resend` so callers can
    import a single name from :mod:`app.services.email` instead of
    threading the provider module through the codebase.
    """
    return send_email_via_resend(
        to=to,
        subject=subject,
        html=html,
        text=text,
        from_email=from_email,
        reply_to=reply_to,
        headers=headers,
    )


def send_password_reset_email(
    *, email_to: str, token: str, full_name: str | None = None
) -> ResendSendResult:
    """Build and send the password-reset email.

    Reuses the existing Jinja template (``email-templates/build/
    reset_password.html``) so the rendered HTML is unchanged from
    the SMTP-era output — only the transport flips to Resend.

    The link the user clicks is built from ``settings.FRONTEND_HOST``
    (the public origin of the SPA), so production sets
    ``FRONTEND_HOST=https://aisignal.now`` and the email link points
    at the production reset page. Token generation lives in
    ``app.utils`` and is unchanged.
    """
    email_data = generate_reset_password_email(
        email_to=email_to, email=email_to, token=token, full_name=full_name
    )
    return send_email(
        to=email_to,
        subject=email_data.subject,
        html=email_data.html_content,
    )


def send_new_account_email(
    *, email_to: str, username: str, password: str
) -> ResendSendResult:
    """Welcome email for a superuser-created account.

    Used by the ``POST /users/`` admin endpoint when a superuser
    provisions an account on behalf of a user. The body includes the
    initial credentials so the user can sign in and rotate them.
    """
    email_data = generate_new_account_email(
        email_to=email_to, username=username, password=password
    )
    return send_email(
        to=email_to,
        subject=email_data.subject,
        html=email_data.html_content,
    )


def send_test_email(*, email_to: str) -> ResendSendResult:
    """Admin "send test email" endpoint payload.

    Lets an operator confirm Resend credentials and the
    ``EMAILS_FROM_EMAIL`` sender are wired correctly without having
    to trigger a real password recovery or digest send.
    """
    email_data = generate_test_email(email_to=email_to)
    return send_email(
        to=email_to,
        subject=email_data.subject,
        html=email_data.html_content,
    )


__all__ = [
    "ResendSendResult",
    "send_digest_email",
    "send_email",
    "send_new_account_email",
    "send_password_reset_email",
    "send_test_email",
]
