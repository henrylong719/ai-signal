"""POST /subscriptions — public endpoint for the daily digest signup form.

Anonymous (no auth). Idempotent: re-submitting an existing email returns
the same 201 as a brand-new one. Deliberately indistinguishable — a
status split (200 vs 201) would let anyone probe which addresses are
already on the subscriber list.
"""

from fastapi import APIRouter, Request, status

from app import crud
from app.api.deps import SessionDep
from app.core.rate_limit import limiter
from app.schemas import SubscriptionCreate, SubscriptionPublic

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
    return SubscriptionPublic.model_validate(subscriber)
