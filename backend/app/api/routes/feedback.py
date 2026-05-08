"""POST /users/me/feedback — lightweight product feedback intake."""

from fastapi import APIRouter, status

from app import crud
from app.api.deps import CurrentUser, SessionDep
from app.schemas import FeedbackCreate, FeedbackPublic

router = APIRouter(prefix="/users/me/feedback", tags=["feedback"])


@router.post("", response_model=FeedbackPublic, status_code=status.HTTP_201_CREATED)
def submit_feedback(
    session: SessionDep,
    current_user: CurrentUser,
    body: FeedbackCreate,
) -> FeedbackPublic:
    feedback = crud.create_feedback(
        session=session,
        user_id=current_user.id,
        feedback_in=body,
    )
    return FeedbackPublic.model_validate(feedback)
