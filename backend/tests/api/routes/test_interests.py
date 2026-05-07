from fastapi.testclient import TestClient
from sqlmodel import Session

from app import crud
from app.core.config import settings
from app.models import User
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


def test_read_interests_requires_auth(client: TestClient) -> None:
    response = client.get(f"{settings.API_V1_STR}/users/me/interests")

    assert response.status_code == 401


def test_read_interests_returns_empty_defaults_for_new_user(
    client: TestClient,
    db: Session,
) -> None:
    _, headers = _create_authenticated_user(client, db)

    response = client.get(
        f"{settings.API_V1_STR}/users/me/interests",
        headers=headers,
    )

    assert response.status_code == 200
    assert response.json() == {
        "categories": [],
        "tags": [],
        "preferred_sources": [],
        "updated_at": None,
    }


def test_update_interests_normalizes_and_replaces_current_user_interests(
    client: TestClient,
    db: Session,
) -> None:
    _, headers = _create_authenticated_user(client, db)

    first = client.put(
        f"{settings.API_V1_STR}/users/me/interests",
        headers=headers,
        json={
            "categories": ["rag", "models"],
            "tags": [" RAG ", "Agents", "", "rag", "x" * 33],
            "preferred_sources": ["OpenAI", "Anthropic"],
        },
    )
    second = client.put(
        f"{settings.API_V1_STR}/users/me/interests",
        headers=headers,
        json={
            "categories": ["agents"],
            "tags": [" Tool Use ", "tool use", "Evals"],
            "preferred_sources": ["LangChain"],
        },
    )
    read_back = client.get(
        f"{settings.API_V1_STR}/users/me/interests",
        headers=headers,
    )

    assert first.status_code == 200
    assert first.json()["categories"] == ["models", "rag"]
    assert first.json()["tags"] == ["agents", "rag"]
    assert first.json()["preferred_sources"] == ["Anthropic", "OpenAI"]
    assert first.json()["updated_at"] is not None
    assert second.status_code == 200
    assert second.json()["categories"] == ["agents"]
    assert second.json()["tags"] == ["evals", "tool use"]
    assert second.json()["preferred_sources"] == ["LangChain"]
    assert read_back.json() == second.json()


def test_update_interests_rejects_unknown_category(
    client: TestClient,
    db: Session,
) -> None:
    _, headers = _create_authenticated_user(client, db)

    response = client.put(
        f"{settings.API_V1_STR}/users/me/interests",
        headers=headers,
        json={"categories": ["quantum"], "tags": [], "preferred_sources": []},
    )

    assert response.status_code == 422


def test_update_interests_rejects_unknown_source(
    client: TestClient,
    db: Session,
) -> None:
    """Source names must match the canonical SOURCES list exactly."""
    _, headers = _create_authenticated_user(client, db)

    response = client.put(
        f"{settings.API_V1_STR}/users/me/interests",
        headers=headers,
        json={
            "categories": [],
            "tags": [],
            "preferred_sources": ["NotARealSource"],
        },
    )

    assert response.status_code == 422


def test_update_interests_dedupes_preferred_sources(
    client: TestClient,
    db: Session,
) -> None:
    _, headers = _create_authenticated_user(client, db)

    response = client.put(
        f"{settings.API_V1_STR}/users/me/interests",
        headers=headers,
        json={
            "categories": [],
            "tags": [],
            "preferred_sources": ["OpenAI", "OpenAI", "Anthropic"],
        },
    )

    assert response.status_code == 200
    # Sorted in storage; OpenAI appears once.
    assert response.json()["preferred_sources"] == ["Anthropic", "OpenAI"]


def test_update_interests_rejects_source_with_wrong_case(
    client: TestClient,
    db: Session,
) -> None:
    """Source matching is case-sensitive — display name is the identifier."""
    _, headers = _create_authenticated_user(client, db)

    response = client.put(
        f"{settings.API_V1_STR}/users/me/interests",
        headers=headers,
        json={
            "categories": [],
            "tags": [],
            "preferred_sources": ["openai"],  # lowercase, not the canonical "OpenAI"
        },
    )

    assert response.status_code == 422
