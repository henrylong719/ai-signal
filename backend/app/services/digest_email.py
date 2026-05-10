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
from app.services.digest import DigestPublic, build_digest
from app.services.resend_email import (
    ResendSendResult,
    send_email_via_resend,
)

logger = logging.getLogger(__name__)


# --- Tokens -----------------------------------------------------------------

_UNSUB_TOKEN_TYPE = "digest-unsub"
_UNSUB_TOKEN_TTL = timedelta(days=30)
_EMAIL_ARTICLE_LIMIT = 8


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


def _format_category(category: str | None) -> str:
    return (category or "").replace("_", " ").title()


def _iter_email_articles(
    digest: DigestPublic,
    *,
    limit: int = _EMAIL_ARTICLE_LIMIT,
) -> list[Article]:
    """Flatten the built digest for email without changing digest ranking."""
    items: list[Article] = []
    for section in digest.sections:
        for article in section.articles:
            items.append(article)
            if len(items) >= limit:
                return items
    return items


def _render_article(article: Article) -> str:
    """One editorial article row. Inline styles only — email clients strip CSS."""
    redirect = _escape(_article_redirect_url(article.id))
    title = _escape(article.title)
    source = _escape(article.source)
    category = _escape(_format_category(article.category))
    excerpt = _escape(article.excerpt or "")
    meta = f"{source} · {category}" if category else source
    excerpt_block = (
        f'<p style="margin:10px 0 0;color:#6F6A61;font-size:14px;'
        f'line-height:22px;">{excerpt}</p>'
        if excerpt
        else ""
    )
    return (
        '<tr><td style="padding:22px 0;border-bottom:1px solid #E6E0D8;">'
        f'<div style="font-size:12px;color:#6F6A61;line-height:18px;'
        f'margin-bottom:7px;">{meta}</div>'
        f'<a href="{redirect}" style="color:#111111;text-decoration:none;'
        'font-family:Georgia,\'Iowan Old Style\',serif;font-size:20px;'
        f'font-weight:600;line-height:28px;">{title}</a>'
        f"{excerpt_block}"
        f'<div style="margin-top:12px;"><a href="{redirect}" '
        'style="color:#111111;text-decoration:none;font-size:14px;'
        'font-weight:600;">Read article &rarr;</a></div>'
        "</td></tr>"
    )


def _render_article_rows(
    digest: DigestPublic,
    *,
    article_limit: int = _EMAIL_ARTICLE_LIMIT,
    empty_message: str | None = None,
) -> str:
    rows = "".join(
        _render_article(article)
        for article in _iter_email_articles(digest, limit=article_limit)
    )
    if not rows and empty_message:
        message = _escape(empty_message)
        rows = (
            '<tr><td style="padding:22px 0;color:#6F6A61;font-size:15px;'
            f'line-height:23px;">{message}</td></tr>'
        )
    return (
        '<table role="presentation" cellpadding="0" cellspacing="0" '
        f'style="width:100%;border-collapse:collapse;">{rows}</table>'
    )


def _render_html(
    *,
    digest: DigestPublic,
    full_name: str | None,
    unsubscribe_url: str,
    settings_url: str,
    home_url: str,
    article_limit: int = _EMAIL_ARTICLE_LIMIT,
    empty_message: str | None = None,
) -> str:
    """Wrap the digest sections in an editorial email shell."""
    first_name = (
        _escape(full_name.split()[0]) if full_name and full_name.strip() else None
    )
    intro = (
        f"Good morning, {first_name}. Here are the AI updates worth your "
        "attention today."
        if first_name
        else "Here are the AI updates worth your attention today."
    )
    article_rows = _render_article_rows(
        digest,
        article_limit=article_limit,
        empty_message=empty_message,
    )
    total_articles = sum(len(section.articles) for section in digest.sections)
    hidden_count = max(total_articles - article_limit, 0)
    continue_note = (
        f'<p style="margin:18px 0 0;color:#6F6A61;font-size:14px;'
        f'line-height:22px;">{hidden_count} more update'
        f'{"s are" if hidden_count != 1 else " is"} waiting in AI Signal.</p>'
        if hidden_count
        else ""
    )
    date_label = _escape(_format_date(digest.generated_at))
    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>AI Signal — Today&rsquo;s Signal</title>
</head>
<body style="margin:0;padding:0;background:#FAFAF8;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,Helvetica,Arial,sans-serif;color:#111111;">
  <table role="presentation" cellpadding="0" cellspacing="0" style="width:100%;background:#FAFAF8;">
    <tr>
      <td align="center" style="padding:40px 16px;">
        <table role="presentation" cellpadding="0" cellspacing="0" style="width:100%;max-width:640px;background:#FFFDF8;border-radius:16px;border:1px solid #E6E0D8;">
          <tr>
            <td style="padding:36px 36px 10px;">
              <div style="font-size:12px;font-weight:700;letter-spacing:0.14em;text-transform:uppercase;color:#6F6A61;">AI Signal</div>
              <h1 style="margin:12px 0 8px;font-family:Georgia,'Iowan Old Style',serif;font-size:34px;line-height:40px;color:#111111;font-weight:500;">Today&rsquo;s Signal</h1>
              <p style="margin:0;color:#6F6A61;font-size:15px;line-height:23px;">{date_label} · A calm briefing of the AI updates worth your attention.</p>
            </td>
          </tr>
          <tr>
            <td style="padding:18px 36px 8px;">
              <p style="margin:0;color:#111111;font-size:16px;line-height:26px;">{intro}</p>
            </td>
          </tr>
          <tr><td style="padding:0 36px 28px;">{article_rows}{continue_note}</td></tr>
          <tr>
            <td align="center" style="padding:0 36px 36px;">
              <a href="{home_url}" style="display:inline-block;background:#111111;color:#FFFFFF;text-decoration:none;border-radius:999px;padding:13px 22px;font-size:14px;font-weight:700;">Open AI Signal</a>
            </td>
          </tr>
          <tr>
            <td style="padding:26px 36px 34px;border-top:1px solid #E6E0D8;background:#FFFFFF;border-radius:0 0 16px 16px;">
              <p style="margin:0 0 4px;font-size:14px;color:#111111;line-height:21px;font-weight:700;">AI Signal</p>
              <p style="margin:0 0 14px;font-size:13px;color:#6F6A61;line-height:20px;">Find the signal in AI updates.</p>
              <p style="margin:0 0 8px;font-size:12px;color:#6F6A61;line-height:19px;">You're receiving this because you opted into AI Signal's daily digest.</p>
              <p style="margin:0;font-size:12px;line-height:19px;">
                <a href="{settings_url}" style="color:#111111;text-decoration:underline;">Manage preferences</a>
                &nbsp;·&nbsp;
                <a href="{unsubscribe_url}" style="color:#6F6A61;text-decoration:underline;">Unsubscribe</a>
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
    intro = (
        f"Good morning, {name_part}. Here are the AI updates worth your "
        "attention today."
        if name_part
        else "Here are the AI updates worth your attention today."
    )
    lines: list[str] = [
        "AI Signal",
        f"Today’s Signal - {_format_date(digest.generated_at)}",
        "",
        intro,
        "",
    ]
    for article in _iter_email_articles(digest):
        redirect = _article_redirect_url(article.id)
        category = _format_category(article.category)
        meta = f"{article.source} · {category}" if category else article.source
        lines.append(article.title)
        lines.append(meta)
        if article.excerpt:
            lines.append(article.excerpt)
        lines.append(f"Read article: {redirect}")
        lines.append("")
    total_articles = sum(len(section.articles) for section in digest.sections)
    hidden_count = max(total_articles - _EMAIL_ARTICLE_LIMIT, 0)
    if hidden_count:
        lines.append(f"{hidden_count} more updates are waiting in AI Signal.")
        lines.append("")
    lines.append(f"Open AI Signal: {home_url}")
    lines.append("AI Signal")
    lines.append("Find the signal in AI updates.")
    lines.append(f"Unsubscribe: {unsubscribe_url}")
    return "\n".join(lines)


# --- Public API -------------------------------------------------------------


def _has_content(digest: DigestPublic) -> bool:
    return any(section.articles for section in digest.sections)


def _digest_email_urls(user: User) -> tuple[str, str, str]:
    token = make_unsubscribe_token(user.id)
    unsubscribe_url = _backend_url("/digest/unsubscribe", {"token": token})
    settings_url = _frontend_url("/settings")
    home_url = _frontend_url("/today-digest")
    return unsubscribe_url, settings_url, home_url


def render_digest_email_html(
    *,
    digest: DigestPublic,
    user: User,
    article_limit: int = _EMAIL_ARTICLE_LIMIT,
    empty_message: str | None = None,
) -> str:
    """Render the same HTML body used by the real digest sender.

    This intentionally stops before the transport layer: callers that need
    preview HTML can reuse the production email shell without touching Resend.
    """
    unsubscribe_url, settings_url, home_url = _digest_email_urls(user)

    return _render_html(
        digest=digest,
        full_name=user.full_name,
        unsubscribe_url=unsubscribe_url,
        settings_url=settings_url,
        home_url=home_url,
        article_limit=article_limit,
        empty_message=empty_message,
    )


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

    subject = f"Today’s Signal — {_format_date(digest.generated_at)}"
    unsubscribe_url, settings_url, home_url = _digest_email_urls(user)
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

    # Bulk traffic (digest) ships from a dedicated sender — typically
    # ``digest@aisignal.now`` — so deliverability problems on the bulk
    # stream don't bleed into the transactional reputation of the
    # password-reset / account address. Falls back to the global
    # transactional sender when only one identity is configured.
    digest_from = (
        str(settings.DIGEST_FROM_EMAIL)
        if settings.DIGEST_FROM_EMAIL
        else (str(settings.EMAILS_FROM_EMAIL) if settings.EMAILS_FROM_EMAIL else None)
    )

    return send_email_via_resend(
        to=user.email,
        subject=subject,
        html=html_body,
        text=text_body,
        from_email=digest_from,
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
    "render_digest_email_html",
    "send_digest_email",
]
