"""CRUD for user feedback submissions."""

import uuid

from sqlmodel import Session

from app.models.base import get_datetime_utc
from app.models.feedback import UserFeedback
from app.schemas.feedback import FeedbackCreate


def create_feedback(
    *,
    session: Session,
    user_id: uuid.UUID,
    feedback_in: FeedbackCreate,
) -> UserFeedback:
    now = get_datetime_utc()
    feedback = UserFeedback(
        user_id=user_id,
        category=feedback_in.category,
        message=feedback_in.message,
        context=feedback_in.context,
        created_at=now,
        updated_at=now,
    )
    session.add(feedback)
    session.commit()
    session.refresh(feedback)
    return feedback
