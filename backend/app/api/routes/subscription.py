"""POST /subscriptions — public endpoint for the daily digest signup form.

Anonymous (no auth). Idempotent: re-submitting an existing email returns
200 with the existing record; a brand-new email returns 201.
"""

from fastapi import APIRouter, Response, status

from app import crud
from app.api.deps import SessionDep
from app.schemas import SubscriptionCreate, SubscriptionPublic

router = APIRouter(prefix="/subscriptions", tags=["subscriptions"])


@router.post(
    "",
    response_model=SubscriptionPublic,
    status_code=status.HTTP_201_CREATED,
)
def create_subscription(
    session: SessionDep,
    body: SubscriptionCreate,
    response: Response,
) -> SubscriptionPublic:
    subscriber, created = crud.upsert_subscriber(
        session=session,
        email=body.email,
    )
    if not created:
        response.status_code = status.HTTP_200_OK
    return SubscriptionPublic.model_validate(subscriber)
