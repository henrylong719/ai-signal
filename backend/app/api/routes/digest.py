from datetime import datetime
from typing import Any

from fastapi import APIRouter, Query
from fastapi.responses import HTMLResponse
from sqlmodel import SQLModel

from app.api.deps import OptionalCurrentUser, SessionDep
from app.core.config import settings
from app.models import User
from app.models.base import get_datetime_utc
from app.schemas import ArticlePublic
from app.services.digest import DigestPublic, DigestSection, build_digest
from app.services.digest_email import parse_unsubscribe_token

router = APIRouter(prefix="/digest", tags=["digest"])


# --- Wire schemas -----------------------------------------------------------
#
# These mirror the dataclasses in services.digest but project Article
# rows down to ArticlePublic (the same shape /articles/ returns) and
# attach the per-article `reason` inline — same pattern as
# ForYouArticlePublic in services/for_you.


class DigestArticlePublic(ArticlePublic):
    """ArticlePublic plus the recommender's reason string.

    Matches ForYouArticlePublic's shape so the frontend can reuse the
    same article-card rendering and reason-badge component.
    """

    reason: str | None = None


class DigestSectionPublic(SQLModel):
    key: str
    title: str
    articles: list[DigestArticlePublic]


class DigestPublicSchema(SQLModel):
    generated_at: datetime
    window_start: datetime
    is_personalized: bool
    sections: list[DigestSectionPublic]


# --- Serialization ----------------------------------------------------------


def _serialize_section(section: DigestSection) -> DigestSectionPublic:
    articles = [
        DigestArticlePublic(
            **ArticlePublic.model_validate(article).model_dump(),
            reason=section.reasons.get(article.id),
        )
        for article in section.articles
    ]
    return DigestSectionPublic(
        key=section.key,
        title=section.title,
        articles=articles,
    )


def _serialize_digest(digest: DigestPublic) -> DigestPublicSchema:
    return DigestPublicSchema(
        generated_at=digest.generated_at,
        window_start=digest.window_start,
        is_personalized=digest.is_personalized,
        sections=[_serialize_section(s) for s in digest.sections],
    )


# --- Route ------------------------------------------------------------------


@router.get("/today-digest", response_model=DigestPublicSchema)
def read_today_digest(
    session: SessionDep,
    user: OptionalCurrentUser,
) -> Any:
    """Today's digest. Personalized when signed in, generic when not."""
    digest = build_digest(
        session=session,
        user_id=user.id if user is not None else None,
    )
    return _serialize_digest(digest)


# --- Unsubscribe ------------------------------------------------------------
#
# Reachable from the link in every digest email AND from the
# List-Unsubscribe header (one-click). Both paths land on the same
# endpoint with a signed token; we flip the user's opt-in flag and
# render a small HTML confirmation. No auth required — possession of
# the signed token is the authorization.

_UNSUB_PAGE_TEMPLATE = """<!doctype html>
<html lang="en"><head><meta charset="utf-8"><title>{title} — AI Signal</title>
<meta name="viewport" content="width=device-width,initial-scale=1">
<style>
body {{ margin:0; background:#f8fafc; color:#0f172a;
       font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,Helvetica,Arial,sans-serif; }}
.card {{ max-width:520px; margin:80px auto; padding:40px;
       background:#fff; border:1px solid #e2e8f0; border-radius:12px;
       box-shadow:0 1px 2px rgba(15,23,42,.04); }}
h1 {{ font-family:Georgia,'Iowan Old Style',serif; font-size:24px; margin:0 0 12px; }}
p  {{ font-size:15px; line-height:23px; color:#475569; margin:0 0 16px; }}
.actions {{ margin-top:20px; display:flex; gap:12px; flex-wrap:wrap; align-items:center; }}
.actions form {{ margin:0; }}
.btn {{ display:inline-block; padding:10px 18px; border-radius:999px;
       font-size:14px; font-weight:600; text-decoration:none;
       border:1px solid #0f172a; cursor:pointer; font-family:inherit; }}
.btn-primary {{ background:#0f172a; color:#fff; }}
.btn-secondary {{ background:#fff; color:#0f172a; }}
</style></head>
<body><div class="card">
<h1>{title}</h1>
<p>{body}</p>
<div class="actions">{actions}</div>
</div></body></html>"""


def _render_page(
    *,
    title: str,
    body: str,
    home_url: str,
    resubscribe_token: str | None = None,
) -> str:
    """Render the shared confirmation page.

    When ``resubscribe_token`` is supplied, the page surfaces a POST
    form that re-enables the digest using the same signed token. The
    JWT alphabet is URL-safe, so the token can sit in the form action
    as a query param without further encoding.
    """
    if resubscribe_token:
        resub_url = (
            f"{settings.API_V1_STR}/digest/resubscribe?token={resubscribe_token}"
        )
        actions = (
            f'<form method="post" action="{resub_url}">'
            '<button type="submit" class="btn btn-primary">Resubscribe</button>'
            "</form>"
            f'<a class="btn btn-secondary" href="{home_url}">Open AI Signal</a>'
        )
    else:
        actions = f'<a class="btn btn-secondary" href="{home_url}">Back to AI Signal</a>'
    return _UNSUB_PAGE_TEMPLATE.format(title=title, body=body, actions=actions)


def _invalid_token_response(home_url: str) -> HTMLResponse:
    return HTMLResponse(
        _render_page(
            title="Link expired",
            body=(
                "This link is invalid or has expired. You can manage "
                "email preferences from your AI Signal account settings."
            ),
            home_url=home_url,
        ),
        status_code=200,
    )


@router.get("/unsubscribe", response_class=HTMLResponse, include_in_schema=False)
def digest_unsubscribe(
    session: SessionDep,
    token: str = Query(..., min_length=1, max_length=4096),
) -> HTMLResponse:
    """Disable the daily digest for the user identified by ``token``.

    Idempotent — repeated clicks land the user on the same confirmation
    page without raising. Always 200 (even on bad tokens) so the email
    client doesn't surface a scary error UI; the body explains the
    state.
    """
    home_url = settings.FRONTEND_HOST.rstrip("/") + "/"
    user_id = parse_unsubscribe_token(token)
    if user_id is None:
        return _invalid_token_response(home_url)

    user = session.get(User, user_id)
    if user is None:
        # The account was deleted after the email was sent. Show the
        # same generic confirmation — no point distinguishing this
        # case to a recipient who can't act on it. No resubscribe
        # button: there's no account to re-enable.
        return HTMLResponse(
            _render_page(
                title="You're unsubscribed",
                body="You will no longer receive daily digest emails from AI Signal.",
                home_url=home_url,
            ),
            status_code=200,
        )

    if user.daily_digest_enabled:
        user.daily_digest_enabled = False
        # Reset the send watermark so a future re-subscribe doesn't
        # silently skip "already sent today" on the same calendar day.
        user.last_digest_sent_at = get_datetime_utc()
        session.add(user)
        session.commit()

    return HTMLResponse(
        _render_page(
            title="You've been unsubscribed from Today's Signal",
            body=(
                "You will no longer receive daily digest emails from AI Signal. "
                "Changed your mind? Resubscribe with one click below."
            ),
            home_url=home_url,
            resubscribe_token=token,
        ),
        status_code=200,
    )


@router.post("/unsubscribe", response_class=HTMLResponse, include_in_schema=False)
def digest_unsubscribe_one_click(
    session: SessionDep,
    token: str = Query(..., min_length=1, max_length=4096),
) -> HTMLResponse:
    """One-click unsubscribe target referenced by the email's
    ``List-Unsubscribe`` header. Same effect as the GET — kept as a
    separate handler so RFC 8058 compliant clients can POST without
    falling through to the GET error page.
    """
    return digest_unsubscribe(session=session, token=token)


# --- Resubscribe ------------------------------------------------------------
#
# Reached only from the Resubscribe button on the unsubscribe
# confirmation page (HTML form POST). Reuses the same signed token —
# no new token type — so a successful unsubscribe + immediate re-opt-in
# travels on one credential. Idempotent. No auth required; possession
# of the signed token is the authorization.


@router.post("/resubscribe", response_class=HTMLResponse, include_in_schema=False)
def digest_resubscribe(
    session: SessionDep,
    token: str = Query(..., min_length=1, max_length=4096),
) -> HTMLResponse:
    """Re-enable the daily digest for the user identified by ``token``."""
    home_url = settings.FRONTEND_HOST.rstrip("/") + "/"
    user_id = parse_unsubscribe_token(token)
    if user_id is None:
        return _invalid_token_response(home_url)

    user = session.get(User, user_id)
    if user is not None and not user.daily_digest_enabled:
        user.daily_digest_enabled = True
        session.add(user)
        session.commit()

    # Generic confirmation regardless of whether the account still
    # exists — same privacy posture as /unsubscribe.
    return HTMLResponse(
        _render_page(
            title="You're subscribed again",
            body="You'll receive Today's Signal in your inbox.",
            home_url=home_url,
        ),
        status_code=200,
    )
