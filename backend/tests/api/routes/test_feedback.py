import uuid

from fastapi.testclient import TestClient
from sqlmodel import Session, select

from app import crud
from app.core.config import settings
from app.models import User, UserFeedback
from app.schemas import UserCreate
from tests.utils.user import user_authentication_headers
from tests.utils.utils import random_email, random_lower_string


def _create_authenticated_user(
    client: TestClient,
    db: Session,
) -> tuple[User, dict[str, str]]:
    email = random_email()
    password = random_lower_string()
    user = crud.create_user(
        session=db,
        user_create=UserCreate(email=email, password=password),
    )
    return user, user_authentication_headers(
        client=client, email=email, password=password
    )


def test_submit_feedback_requires_auth(client: TestClient) -> None:
    response = client.post(
        f"{settings.API_V1_STR}/users/me/feedback",
        json={
            "category": "general",
            "message": "This is helpful feedback from a reader.",
        },
    )

    assert response.status_code == 401


def test_submit_feedback_persists_current_user_submission(
    client: TestClient,
    db: Session,
) -> None:
    user, headers = _create_authenticated_user(client, db)

    response = client.post(
        f"{settings.API_V1_STR}/users/me/feedback",
        headers=headers,
        json={
            "category": "missing_topic_source_tag",
            "message": "Please add more coverage for agent evaluation sources.",
            "context": {"path": "/personalization", "source": "settings"},
        },
    )

    assert response.status_code == 201
    body = response.json()
    assert body["user_id"] == str(user.id)
    assert body["category"] == "missing_topic_source_tag"
    assert body["message"] == "Please add more coverage for agent evaluation sources."
    assert body["context"] == {"path": "/personalization", "source": "settings"}
    assert body["created_at"] is not None
    assert body["updated_at"] is not None

    statement = select(UserFeedback).where(UserFeedback.id == uuid.UUID(body["id"]))
    stored = db.exec(statement).one()
    assert stored.user_id == user.id
    assert stored.category == "missing_topic_source_tag"
    assert stored.message == body["message"]
    assert stored.context == body["context"]


def test_submit_feedback_rejects_unknown_category(
    client: TestClient,
    db: Session,
) -> None:
    _, headers = _create_authenticated_user(client, db)

    response = client.post(
        f"{settings.API_V1_STR}/users/me/feedback",
        headers=headers,
        json={
            "category": "roadmap",
            "message": "This category should not be accepted.",
        },
    )

    assert response.status_code == 422


def test_submit_feedback_rejects_short_message(
    client: TestClient,
    db: Session,
) -> None:
    _, headers = _create_authenticated_user(client, db)

    response = client.post(
        f"{settings.API_V1_STR}/users/me/feedback",
        headers=headers,
        json={"category": "bug_report", "message": "Too short"},
    )

    assert response.status_code == 422
