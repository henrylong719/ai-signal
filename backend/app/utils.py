"""Email-content rendering and password-reset token helpers.

Historically this module also owned the SMTP send path via the
``emails`` PyPI package. App email is now uniformly delivered
through Resend; see :mod:`app.services.email`. The legacy
``send_email(...)`` function below is kept as a back-compat shim
that delegates to the new service so any caller still importing
``from app.utils import send_email`` continues to work.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import jwt
from jinja2 import Template
from jwt.exceptions import InvalidTokenError

from app.core import security
from app.core.config import settings

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@dataclass
class EmailData:
    html_content: str
    subject: str


def render_email_template(*, template_name: str, context: dict[str, Any]) -> str:
    template_str = (
        Path(__file__).parent / "email-templates" / "build" / template_name
    ).read_text()
    html_content = Template(template_str).render(context)
    return html_content


def send_email(
    *,
    email_to: str,
    subject: str = "",
    html_content: str = "",
) -> None:
    """Back-compat shim that routes legacy callers through Resend.

    Pre-refactor this opened an SMTP connection via the ``emails``
    package. Existing call sites and test patches (``patch(
    "app.utils.send_email")``) keep working because the symbol is
    still here — but the actual transport is now Resend, via
    :func:`app.services.email.send_email`. New code should import
    from :mod:`app.services.email` directly.

    Errors are swallowed (logged only) to preserve the previous
    behavior, where transient SMTP failures didn't bubble up out of
    the request handler that triggered the send. Callers that need
    to branch on success should use the service layer directly so
    they get a structured ``ResendSendResult`` back.
    """
    # Imported lazily to avoid a circular import: services/email.py
    # imports the generate_*_email helpers from this module.
    from app.services.email import send_email as _send_email_via_service

    result = _send_email_via_service(to=email_to, subject=subject, html=html_content)
    if not result.ok:
        logger.warning(
            "send_email shim: Resend send failed (to=%s): %s",
            email_to,
            result.error,
        )


def generate_test_email(email_to: str) -> EmailData:
    project_name = settings.PROJECT_NAME
    subject = f"{project_name} - Test email"
    html_content = render_email_template(
        template_name="test_email.html",
        context={"project_name": settings.PROJECT_NAME, "email": email_to},
    )
    return EmailData(html_content=html_content, subject=subject)


def _password_reset_greeting(full_name: str | None) -> str:
    first_name = (
        full_name.strip().split()[0] if full_name and full_name.strip() else None
    )
    if not first_name:
        return "Hi,"
    display_name = first_name.title() if first_name.isupper() else first_name
    return f"Hi {display_name},"


def generate_reset_password_email(
    email_to: str, email: str, token: str, full_name: str | None = None
) -> EmailData:
    """Render the password-reset email body and subject.

    ``link`` is built from ``settings.FRONTEND_HOST`` so production
    (``https://aisignal.now``) and local dev (``http://localhost:5173``)
    each get a working reset URL without the email-rendering code
    needing to know which environment it is running in.
    """
    subject = "Reset your AI Signal password"
    link = f"{settings.FRONTEND_HOST.rstrip('/')}/reset-password?token={token}"
    html_content = render_email_template(
        template_name="reset_password.html",
        context={
            "project_name": settings.PROJECT_NAME,
            "username": email,
            "email": email_to,
            "greeting": _password_reset_greeting(full_name),
            "valid_hours": settings.EMAIL_RESET_TOKEN_EXPIRE_HOURS,
            "link": link,
        },
    )
    return EmailData(html_content=html_content, subject=subject)


def generate_new_account_email(
    email_to: str, username: str, password: str
) -> EmailData:
    project_name = settings.PROJECT_NAME
    subject = f"{project_name} - New account for user {username}"
    html_content = render_email_template(
        template_name="new_account.html",
        context={
            "project_name": settings.PROJECT_NAME,
            "username": username,
            "password": password,
            "email": email_to,
            "link": settings.FRONTEND_HOST,
        },
    )
    return EmailData(html_content=html_content, subject=subject)


def generate_password_reset_token(email: str) -> str:
    delta = timedelta(hours=settings.EMAIL_RESET_TOKEN_EXPIRE_HOURS)
    now = datetime.now(timezone.utc)
    expires = now + delta
    exp = expires.timestamp()
    encoded_jwt = jwt.encode(
        {"exp": exp, "nbf": now, "sub": email},
        settings.SECRET_KEY,
        algorithm=security.ALGORITHM,
    )
    return encoded_jwt


def verify_password_reset_token(token: str) -> str | None:
    try:
        decoded_token = jwt.decode(
            token, settings.SECRET_KEY, algorithms=[security.ALGORITHM]
        )
        return str(decoded_token["sub"])
    except InvalidTokenError:
        return None
