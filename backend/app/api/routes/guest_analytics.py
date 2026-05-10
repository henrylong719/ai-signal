"""Public guest analytics intake + admin funnel summary.

Two routes, two audiences:

- ``POST /analytics/guest-event`` is public (no auth). It accepts a
  small JSON payload from logged-out browsers, validates it strictly,
  and inserts one row. Failures never block the caller — the client
  treats analytics as best-effort and the server returns 202 so a
  truthful "we accepted it for processing" status is communicated
  even when the persist itself silently fails.

- ``GET /admin/analytics/guest-funnel`` is superuser-only and returns
  the dashboard payload (cards + tables + CTA performance). All shaping
  lives here; the CRUD layer just returns raw aggregations.
"""

import logging
from datetime import datetime, timedelta, timezone
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status

from app import crud
from app.api.deps import SessionDep, get_current_active_superuser
from app.core.rate_limit import limiter
from app.models.guest_event import GUEST_EVENT_TYPES
from app.schemas import (
    ALLOWED_RANGES,
    CtaLocationRow,
    DateRange,
    FunnelCounts,
    FunnelRates,
    GuestEventCreate,
    GuestFunnelResponse,
    TopArticleRow,
    TopSourceRow,
    TopTopicRow,
)
from app.schemas.common import Message

logger = logging.getLogger(__name__)


# Map ``range`` query param to a lookback ``timedelta``. ``"all"`` is the
# sentinel for no lower bound (returns ``None`` from ``_range_to_since``).
_RANGE_TO_TIMEDELTA: dict[str, timedelta] = {
    "7d": timedelta(days=7),
    "30d": timedelta(days=30),
    "90d": timedelta(days=90),
}


def _range_to_since(range_value: DateRange, now: datetime) -> datetime | None:
    if range_value == "all":
        return None
    delta = _RANGE_TO_TIMEDELTA.get(range_value)
    if delta is None:
        # ``DateRange`` is a Literal, so FastAPI rejects bad values before
        # we get here; this branch is defensive only.
        raise HTTPException(status_code=400, detail=f"Unknown range {range_value!r}")
    return now - delta


# --- Public intake ---


public_router = APIRouter(prefix="/analytics", tags=["analytics"])


@public_router.post(
    "/guest-event",
    response_model=Message,
    status_code=status.HTTP_202_ACCEPTED,
)
@limiter.limit("120/minute")
def record_guest_event(
    request: Request,  # noqa: ARG001  # consumed by @limiter.limit (per-IP key)
    session: SessionDep,
    body: GuestEventCreate,
) -> Any:
    """Record a single anonymous funnel event.

    Returns 202 even when the underlying insert fails: the client treats
    analytics as best-effort and we don't want a transient DB hiccup to
    surface as a noisy error in the SPA console (the network log already
    shows the failure for operators inspecting traffic).
    """
    try:
        crud.record_guest_event(
            session=session,
            anonymous_id=body.anonymous_id,
            event_type=body.event_type,
            user_id=body.user_id,
            path=body.path,
            article_id=body.article_id,
            source_name=body.source_id,
            topic=body.topic,
            referrer=body.referrer,
            event_metadata=body.event_metadata,
        )
    except Exception:  # noqa: BLE001 -- intentionally broad; analytics is best-effort
        session.rollback()
        logger.exception("Failed to record guest event: %s", body.event_type)
    return Message(message="accepted")


# --- Admin summary ---


admin_router = APIRouter(
    prefix="/admin",
    tags=["admin"],
    dependencies=[Depends(get_current_active_superuser)],
)


def _zero_safe_ratio(numerator: int, denominator: int) -> float:
    if denominator <= 0:
        return 0.0
    return numerator / denominator


@admin_router.get(
    "/analytics/guest-funnel",
    response_model=GuestFunnelResponse,
)
def read_guest_funnel(
    session: SessionDep,
    range_: Annotated[DateRange, Query(alias="range")] = "30d",
    top_limit: Annotated[int, Query(ge=1, le=50)] = 10,
) -> Any:
    """Aggregate the anonymous funnel for the admin dashboard."""
    if range_ not in ALLOWED_RANGES:
        # Defense in depth — Literal validation catches this first.
        raise HTTPException(status_code=400, detail="Unknown range")

    now = datetime.now(timezone.utc)
    since = _range_to_since(range_, now)

    raw_counts = crud.get_event_counts_by_type(session=session, since=since, until=now)
    counts = FunnelCounts(
        **{
            event_type: raw_counts.get(event_type, 0)
            for event_type in GUEST_EVENT_TYPES
        }
    )

    rates = FunnelRates(
        article_click_rate=_zero_safe_ratio(
            counts.guest_article_click, counts.guest_page_view
        ),
        signup_click_rate=_zero_safe_ratio(
            counts.guest_signup_click, counts.guest_page_view
        ),
        signup_conversion_rate=_zero_safe_ratio(
            counts.guest_signup_completed, counts.guest_signup_click
        ),
    )

    top_articles_raw = crud.get_top_clicked_articles(
        session=session, since=since, until=now, limit=top_limit
    )
    top_articles = [
        TopArticleRow(
            article_id=article_id,
            title=getattr(article, "title", None),
            source_name=getattr(article, "source", None),
            url=getattr(article, "url", None),
            published_at=getattr(article, "published_at", None),
            guest_clicks=clicks,
        )
        for article_id, clicks, article in top_articles_raw
    ]

    top_sources = [
        TopSourceRow(source_name=name, guest_clicks=clicks)
        for name, clicks in crud.get_top_clicked_sources(
            session=session, since=since, until=now, limit=top_limit
        )
    ]
    top_topics = [
        TopTopicRow(topic=name, guest_clicks=clicks)
        for name, clicks in crud.get_top_clicked_topics(
            session=session, since=since, until=now, limit=top_limit
        )
    ]
    cta_rows = [
        CtaLocationRow(location=location, clicks=clicks)
        for location, clicks in crud.get_signup_cta_clicks_by_location(
            session=session, since=since, until=now
        )
    ]

    return GuestFunnelResponse(
        range=range_,
        range_start=since,
        range_end=now,
        counts=counts,
        rates=rates,
        top_articles=top_articles,
        top_sources=top_sources,
        top_topics=top_topics,
        signup_cta_locations=cta_rows,
    )


# Single router exported to keep ``api.main`` includes one-line each.
# Re-exposes both the public intake and the admin summary.
router = APIRouter()
router.include_router(public_router)
router.include_router(admin_router)
