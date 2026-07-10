"""Public digest-subscription endpoints.

Anonymous (no auth). Single opt-in: subscribing activates the address
immediately and sends today's digest as a welcome. The unsubscribe
endpoints are reachable from the link in every subscriber digest (and its
``List-Unsubscribe`` header); possession of the signed token is the
authorization.

``POST /subscriptions`` returns 201 for both new and existing emails —
deliberately indistinguishable, so a status split can't be used to probe
which addresses are already on the list.
"""

import logging

from fastapi import APIRouter, Query, Request, status
from fastapi.responses import HTMLResponse

from app import crud
from app.api.deps import SessionDep
from app.api.routes.digest import _render_page
from app.core.config import settings
from app.core.rate_limit import limiter
from app.models.base import get_datetime_utc
from app.schemas import SubscriptionCreate, SubscriptionPublic
from app.services.subscriber_email import (
    already_sent_on_utc_day,
    send_subscriber_digest_email,
)
from app.services.subscriber_tokens import parse_subscriber_unsubscribe_token

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/subscriptions", tags=["subscriptions"])


@router.post(
    "",
    response_model=SubscriptionPublic,
    status_code=status.HTTP_201_CREATED,
)
@limiter.limit("10/minute")
def create_subscription(
    request: Request,  # noqa: ARG001  # consumed by @limiter.limit
    session: SessionDep,
    body: SubscriptionCreate,
) -> SubscriptionPublic:
    subscriber, _created = crud.upsert_subscriber(
        session=session,
        email=body.email,
    )

    # Immediate welcome send — best-effort. A build/render/Resend failure
    # (or an empty digest) must never turn the subscribe into an error;
    # the daily scheduled job will pick the address up on its next run.
    # Guarded by the same-UTC-day watermark so a rapid re-subscribe can't
    # re-mail an address that already got today's digest.
    now = get_datetime_utc()
    if not already_sent_on_utc_day(subscriber, now=now):
        try:
            result = send_subscriber_digest_email(
                session=session, subscriber=subscriber
            )
            if result.ok:
                crud.mark_subscriber_digest_sent(
                    session=session, subscriber=subscriber, now=now
                )
        except Exception:  # noqa: BLE001 -- welcome send is best-effort
            session.rollback()
            logger.exception(
                "Welcome digest send failed for subscriber %s; continuing",
                subscriber.id,
            )

    return SubscriptionPublic.model_validate(subscriber)


def _subscriber_home_url() -> str:
    return settings.FRONTEND_HOST.rstrip("/") + "/digest"


def _unsubscribe(session: SessionDep, token: str) -> HTMLResponse:
    """Deactivate the subscriber named by ``token`` and render a page.

    Always 200 — even on a bad token — so a mail client never surfaces a
    scary error UI; the body explains the state. Idempotent.
    """
    home_url = _subscriber_home_url()
    subscriber_id = parse_subscriber_unsubscribe_token(token)
    if subscriber_id is None:
        return HTMLResponse(
            _render_page(
                title="Link expired",
                body=(
                    "This unsubscribe link is invalid or has expired. If you "
                    "keep receiving emails, reply and let us know."
                ),
                home_url=home_url,
            ),
            status_code=200,
        )

    crud.unsubscribe_subscriber(session=session, subscriber_id=subscriber_id)
    return HTMLResponse(
        _render_page(
            title="You've been unsubscribed",
            body="You will no longer receive the daily AI Signal digest.",
            home_url=home_url,
        ),
        status_code=200,
    )


@router.get("/unsubscribe", response_class=HTMLResponse, include_in_schema=False)
def unsubscribe_get(
    session: SessionDep,
    token: str = Query(..., min_length=1, max_length=4096),
) -> HTMLResponse:
    return _unsubscribe(session, token)


@router.post("/unsubscribe", response_class=HTMLResponse, include_in_schema=False)
def unsubscribe_post(
    session: SessionDep,
    token: str = Query(..., min_length=1, max_length=4096),
) -> HTMLResponse:
    """RFC 8058 one-click target referenced by the digest's
    ``List-Unsubscribe`` header. Same effect as the GET."""
    return _unsubscribe(session, token)
