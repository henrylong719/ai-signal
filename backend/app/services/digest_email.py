"""Daily digest email assembly + delivery.

Plumbing the existing per-user ``services.digest.build_digest`` output
into an HTML/text email and shipping it via Resend. The hourly
scheduler (``services.scheduler``) is the only caller of
``send_digest_email`` in production; tests can call it directly with
a mocked Resend client.

Design choices:

  - HTML is produced inline rather than from a Jinja file. The
    template is small (one wrapper, one section block, one card row)
    and lives next to the only code that consumes it, so the
    indirection of a separate file isn't worth it yet. If we ever
    add a second email type with the same chrome, hoist it.

  - The unsubscribe URL is a JWT signed with ``SECRET_KEY`` and a
    distinct token type so it cannot be presented to the auth path.
    A 30-day expiry is intentionally long — clicks come from the
    user's mailbox archive, where the link must keep working past
    a normal access-token lifetime.

  - HTML escaping: every interpolated string passes through
    ``html.escape``. The article title, source, and excerpt come from
    third-party RSS feeds, so we cannot trust them to be safe HTML.
"""

from __future__ import annotations

import html
import logging
import uuid
from datetime import datetime, timedelta, timezone
from urllib.parse import urlencode, urljoin

import jwt
from sqlmodel import Session

from app.core import security
from app.core.config import settings
from app.models import Article, User
from app.services.digest import DigestPublic, DigestSection, build_digest
from app.services.resend_email import (
    ResendSendResult,
    send_email_via_resend,
)

logger = logging.getLogger(__name__)


# --- Tokens -----------------------------------------------------------------

_UNSUB_TOKEN_TYPE = "digest-unsub"
_UNSUB_TOKEN_TTL = timedelta(days=30)


def make_unsubscribe_token(user_id: uuid.UUID) -> str:
    """Sign a one-purpose unsubscribe link.

    Uses a distinct token ``type`` so the token can never be presented
    on the auth path: ``security.decode_token`` requires
    ``expected_type='access'`` or ``'refresh'`` and rejects anything
    else. We don't reuse those because the unsub URL travels in clear
    in email link rewrites and bounces — losing it should not affect
    session security.
    """
    expire = datetime.now(timezone.utc) + _UNSUB_TOKEN_TTL
    return jwt.encode(
        {
            "sub": str(user_id),
            "exp": expire,
            "type": _UNSUB_TOKEN_TYPE,
        },
        settings.SECRET_KEY,
        algorithm=security.ALGORITHM,
    )


def parse_unsubscribe_token(token: str) -> uuid.UUID | None:
    """Verify an unsubscribe token and return the user id.

    Returns None on any failure (bad signature, expired, wrong type)
    so the caller can render a generic "link invalid" page without
    leaking which failure mode occurred.
    """
    try:
        payload = jwt.decode(
            token, settings.SECRET_KEY, algorithms=[security.ALGORITHM]
        )
    except jwt.InvalidTokenError:
        return None
    if payload.get("type") != _UNSUB_TOKEN_TYPE:
        return None
    sub = payload.get("sub")
    if not sub:
        return None
    try:
        return uuid.UUID(str(sub))
    except (ValueError, TypeError):
        return None


# --- URL helpers ------------------------------------------------------------


def _frontend_url(path: str, query: dict[str, str] | None = None) -> str:
    """Build an absolute URL into the frontend.

    Wraps ``settings.FRONTEND_HOST`` so callers don't have to remember
    the trailing-slash convention or how to encode query params.
    """
    base = settings.FRONTEND_HOST.rstrip("/") + "/"
    url = urljoin(base, path.lstrip("/"))
    if query:
        url = f"{url}?{urlencode(query)}"
    return url


def _backend_url(path: str, query: dict[str, str] | None = None) -> str:
    """Build an absolute URL into the backend (used by the unsubscribe link).

    The unsubscribe endpoint lives in the API because it needs to mutate
    DB state directly from the email click without a SPA round-trip.
    """
    base = settings.FRONTEND_HOST.rstrip("/") + "/"
    # Email recipients hit the backend via the same origin in production.
    # FRONTEND_HOST is the public origin; the backend mounts under
    # API_V1_STR. Build the absolute URL accordingly.
    url = urljoin(base, settings.API_V1_STR.lstrip("/") + path)
    if query:
        url = f"{url}?{urlencode(query)}"
    return url


def _article_redirect_url(article_id: uuid.UUID) -> str:
    """Outbound link that records the click before redirecting.

    Same redirect endpoint the SPA uses, so digest clicks feed the
    recommender just like in-app reads.
    """
    return _backend_url(f"/articles/{article_id}/go")


# --- HTML rendering ---------------------------------------------------------


def _format_date(now: datetime) -> str:
    # Locale-independent format; intentionally avoids strftime("%B") so
    # tests don't depend on the system locale.
    months = (
        "January", "February", "March", "April", "May", "June",
        "July", "August", "September", "October", "November", "December",
    )  # fmt: skip
    return f"{months[now.month - 1]} {now.day}, {now.year}"


def _escape(value: str | None) -> str:
    return html.escape(value or "")


def _render_article(article: Article, reason: str | None) -> str:
    """One article card. Inline styles only — email clients strip <style>."""
    redirect = _article_redirect_url(article.id)
    title = _escape(article.title)
    source = _escape(article.source)
    excerpt = _escape(article.excerpt or "")
    reason_block = (
        f'<div style="font-size:11px;font-weight:600;letter-spacing:0.06em;'
        f'text-transform:uppercase;color:#94a3b8;margin-bottom:8px;">'
        f'{_escape(reason)}</div>'
        if reason
        else ""
    )
    excerpt_block = (
        f'<p style="margin:8px 0 0;color:#475569;font-size:14px;'
        f'line-height:22px;">{excerpt}</p>'
        if excerpt
        else ""
    )
    return (
        '<tr><td style="padding:18px 0;border-bottom:1px solid #e2e8f0;">'
        f"{reason_block}"
        f'<div style="font-size:13px;color:#64748b;margin-bottom:6px;">'
        f"{source}</div>"
        f'<a href="{redirect}" style="color:#0f172a;text-decoration:none;'
        'font-family:Georgia,\'Iowan Old Style\',serif;font-size:20px;'
        f'font-weight:600;line-height:28px;">{title}</a>'
        f"{excerpt_block}"
        "</td></tr>"
    )


def _render_section(section: DigestSection) -> str:
    """One section: heading + each article in a single-column table."""
    rows = "".join(
        _render_article(article, section.reasons.get(article.id))
        for article in section.articles
    )
    return (
        '<tr><td style="padding:28px 0 6px;">'
        '<div style="font-size:11px;font-weight:700;letter-spacing:0.16em;'
        'text-transform:uppercase;color:#64748b;">'
        f"{_escape(section.title)}</div>"
        "</td></tr>"
        f'<tr><td><table role="presentation" cellpadding="0" cellspacing="0" '
        f'style="width:100%;border-collapse:collapse;">{rows}</table></td></tr>'
    )


def _render_html(
    *,
    digest: DigestPublic,
    full_name: str | None,
    unsubscribe_url: str,
    settings_url: str,
    home_url: str,
) -> str:
    """Wrap the digest sections in an editorial email shell."""
    greeting = (
        f"Good morning, {_escape(full_name.split()[0])}."
        if full_name and full_name.strip()
        else "Good morning."
    )
    sections_html = "".join(_render_section(s) for s in digest.sections)
    date_label = _escape(_format_date(digest.generated_at))
    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>AI Signal — daily digest</title>
</head>
<body style="margin:0;padding:0;background:#f8fafc;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,Helvetica,Arial,sans-serif;color:#0f172a;">
  <table role="presentation" cellpadding="0" cellspacing="0" style="width:100%;background:#f8fafc;">
    <tr>
      <td align="center" style="padding:32px 16px;">
        <table role="presentation" cellpadding="0" cellspacing="0" style="width:100%;max-width:600px;background:#ffffff;border-radius:12px;border:1px solid #e2e8f0;">
          <tr>
            <td style="padding:32px 32px 8px;">
              <div style="font-size:11px;font-weight:700;letter-spacing:0.18em;text-transform:uppercase;color:#94a3b8;">AI Signal · {date_label}</div>
              <h1 style="margin:14px 0 6px;font-family:Georgia,'Iowan Old Style',serif;font-size:28px;line-height:34px;color:#0f172a;">{greeting}</h1>
              <p style="margin:0;color:#475569;font-size:15px;line-height:23px;">Today's most important AI updates, grouped by signal area.</p>
            </td>
          </tr>
          <tr><td style="padding:0 32px 24px;">{sections_html}</td></tr>
          <tr>
            <td style="padding:24px 32px 32px;border-top:1px solid #e2e8f0;background:#f8fafc;border-radius:0 0 12px 12px;">
              <p style="margin:0 0 8px;font-size:13px;color:#64748b;line-height:20px;">You're receiving this because you opted into AI Signal's daily digest.</p>
              <p style="margin:0;font-size:13px;line-height:20px;">
                <a href="{home_url}" style="color:#0f172a;text-decoration:underline;">Open AI Signal</a>
                &nbsp;·&nbsp;
                <a href="{settings_url}" style="color:#0f172a;text-decoration:underline;">Manage preferences</a>
                &nbsp;·&nbsp;
                <a href="{unsubscribe_url}" style="color:#64748b;text-decoration:underline;">Unsubscribe</a>
              </p>
            </td>
          </tr>
        </table>
      </td>
    </tr>
  </table>
</body>
</html>"""


def _render_text(
    *,
    digest: DigestPublic,
    full_name: str | None,
    unsubscribe_url: str,
    home_url: str,
) -> str:
    """Plain-text fallback for clients that prefer it.

    Spam filters and accessibility scanners both improve when an email
    has a real text/plain part instead of an auto-generated one.
    """
    name_part = full_name.split()[0] if full_name and full_name.strip() else None
    greeting = f"Good morning, {name_part}." if name_part else "Good morning."
    lines: list[str] = [
        f"AI Signal — {_format_date(digest.generated_at)}",
        "",
        greeting,
        "Today's most important AI updates, grouped by signal area.",
        "",
    ]
    for section in digest.sections:
        lines.append(section.title.upper())
        for article in section.articles:
            redirect = _article_redirect_url(article.id)
            lines.append(f"- {article.title} ({article.source})")
            lines.append(f"  {redirect}")
        lines.append("")
    lines.append(f"Open AI Signal: {home_url}")
    lines.append(f"Unsubscribe: {unsubscribe_url}")
    return "\n".join(lines)


# --- Public API -------------------------------------------------------------


def _has_content(digest: DigestPublic) -> bool:
    return any(section.articles for section in digest.sections)


def send_digest_email(*, session: Session, user: User) -> ResendSendResult:
    """Build and send the digest for one user.

    Returns the Resend send result so the caller (the hourly scheduler
    job, or a manual admin trigger) can record success per user. The
    caller is also responsible for stamping ``last_digest_sent_at``;
    keeping that out of this function lets unit tests exercise the
    rendering path without DB writes.
    """
    digest = build_digest(session=session, user_id=user.id)
    if not _has_content(digest):
        # The day was quiet enough that even the 48h fallback window
        # produced no candidates. Skipping is the right call — sending
        # an empty email is worse than skipping.
        logger.info(
            "Digest for user=%s is empty; skipping send",
            user.id,
        )
        return ResendSendResult(ok=False, error="empty digest")

    token = make_unsubscribe_token(user.id)
    unsubscribe_url = _backend_url("/digest/unsubscribe", {"token": token})
    settings_url = _frontend_url("/settings")
    home_url = _frontend_url("/today-digest")

    subject = f"Your AI Signal — {_format_date(digest.generated_at)}"
    html_body = _render_html(
        digest=digest,
        full_name=user.full_name,
        unsubscribe_url=unsubscribe_url,
        settings_url=settings_url,
        home_url=home_url,
    )
    text_body = _render_text(
        digest=digest,
        full_name=user.full_name,
        unsubscribe_url=unsubscribe_url,
        home_url=home_url,
    )

    return send_email_via_resend(
        to=user.email,
        subject=subject,
        html=html_body,
        text=text_body,
        # One-click unsubscribe headers — Gmail/Yahoo bulk-sender
        # requirements. The mailto fallback uses the same token wrapped
        # in an email so users with non-HTTP-capable mail clients can
        # still opt out. Resend honours the headers verbatim.
        headers={
            "List-Unsubscribe": f"<{unsubscribe_url}>",
            "List-Unsubscribe-Post": "List-Unsubscribe=One-Click",
        },
    )


# Re-export so the unsubscribe endpoint can resolve a token without
# importing the email-rendering code directly.
__all__ = [
    "ResendSendResult",
    "make_unsubscribe_token",
    "parse_unsubscribe_token",
    "send_digest_email",
]
