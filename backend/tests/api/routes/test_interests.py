from fastapi.testclient import TestClient
from sqlmodel import Session

from app import crud
from app.core.config import settings
from app.models import User
from app.schemas import UserCreate
from app.schemas.source import SOURCES
from tests.utils.user import user_authentication_headers
from tests.utils.utils import random_email, random_lower_string

# Names that shipped in SOURCES and were later retired. RETIRED_SOURCE is the
# one from the original incident; the rest are only needed where a test wants
# several. Defined once here so the fixtures below cannot drift apart, and
# guarded by test_retired_fixture_names_are_not_live_sources — re-adding one of
# these to SOURCES would otherwise turn these regression tests into silent
# no-ops that still pass.
RETIRED_SOURCE = "3Blue1Brown"
MORE_RETIRED_SOURCES = ("sentdex", "Unite.AI")


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


def test_retired_fixture_names_are_not_live_sources() -> None:
    """Guards the fixtures above against SOURCES changing under them.

    Every retired-source test asserts that a name gets dropped. If one of
    these names were ever re-added to SOURCES, those tests would keep
    passing while quietly testing nothing. Fail here instead, with an
    obvious reason.
    """
    live_names = {source.name for source in SOURCES}

    assert not live_names & {RETIRED_SOURCE, *MORE_RETIRED_SOURCES}


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


def test_update_interests_drops_unknown_source(
    client: TestClient,
    db: Session,
) -> None:
    """Unknown source names are dropped, not rejected.

    Sources get retired from SOURCES over time. A client echoing back a
    name the server handed it earlier must not be punished for server-side
    curation — see `test_update_interests_keeps_valid_sources_alongside_retired_one`.
    """
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

    assert response.status_code == 200
    assert response.json()["preferred_sources"] == []


def test_update_interests_keeps_valid_sources_alongside_retired_one(
    client: TestClient,
    db: Session,
) -> None:
    """Regression: a retired name must not block the whole save.

    RETIRED_SOURCE shipped in SOURCES and was later removed. Users who had
    followed it kept it in their stored list, the frontend echoed the full
    list back on every follow/unfollow, and the strict validator 422'd the
    entire payload — locking those users out of changing any source.
    """
    _, headers = _create_authenticated_user(client, db)

    response = client.put(
        f"{settings.API_V1_STR}/users/me/interests",
        headers=headers,
        json={
            "categories": [],
            "tags": [],
            "preferred_sources": [
                RETIRED_SOURCE,
                "OpenAI",
                "GitHub Trending (Daily)",
            ],
        },
    )

    assert response.status_code == 200
    assert response.json()["preferred_sources"] == [
        "GitHub Trending (Daily)",
        "OpenAI",
    ]


def test_update_interests_retired_names_do_not_breach_the_count_cap(
    client: TestClient,
    db: Session,
) -> None:
    """The cap bounds what we store, so it must apply after filtering.

    `preferred_sources` is capped at len(SOURCES). A user who follows
    (nearly) everything and also carries retired names would otherwise
    exceed the cap on the raw payload and get 422'd before the filter
    could drop the dead names — the same lockout by a different route.
    """
    _, headers = _create_authenticated_user(client, db)
    every_live_source = [source.name for source in SOURCES]

    response = client.put(
        f"{settings.API_V1_STR}/users/me/interests",
        headers=headers,
        json={
            "categories": [],
            "tags": [],
            "preferred_sources": every_live_source
            + [RETIRED_SOURCE, *MORE_RETIRED_SOURCES],
        },
    )

    assert response.status_code == 200
    assert response.json()["preferred_sources"] == sorted(every_live_source)


def test_update_interests_bounds_storage_regardless_of_payload_size(
    client: TestClient,
    db: Session,
) -> None:
    """Filtering is what bounds the column, so junk volume can't DOS it.

    The cap moved behind the filter, so a huge payload no longer 422s —
    it collapses to whatever the server actually recognizes. That keeps
    the original guarantee (storage can never exceed len(SOURCES)) while
    removing the failure mode that locked users out.
    """
    _, headers = _create_authenticated_user(client, db)

    response = client.put(
        f"{settings.API_V1_STR}/users/me/interests",
        headers=headers,
        json={
            "categories": [],
            "tags": [],
            "preferred_sources": [f"Junk Source {i}" for i in range(10_000)],
        },
    )

    assert response.status_code == 200
    assert response.json()["preferred_sources"] == []


def test_update_interests_reports_a_type_error_for_non_list_sources(
    client: TestClient,
    db: Session,
) -> None:
    """Malformed input still gets Pydantic's own type error.

    The before-mode validator passes non-list values straight through so
    the error names the declared list[str], rather than the validator
    inventing its own message or silently wrapping the value.
    """
    _, headers = _create_authenticated_user(client, db)

    response = client.put(
        f"{settings.API_V1_STR}/users/me/interests",
        headers=headers,
        json={"categories": [], "tags": [], "preferred_sources": "OpenAI"},
    )

    assert response.status_code == 422
    detail = response.json()["detail"]
    assert detail[0]["type"] == "list_type"
    assert detail[0]["loc"] == ["body", "preferred_sources"]


def test_update_interests_reports_a_type_error_for_non_string_source(
    client: TestClient,
    db: Session,
) -> None:
    """A list holding a non-string is passed through the same way.

    This is the other half of the before-mode passthrough, and the half
    with teeth: the validator must hand the whole list back untouched so
    Pydantic can name the offending element. Dropping the bad item and
    filtering the rest would silently save a shorter list than the client
    sent, which is the one outcome the passthrough exists to prevent.
    """
    _, headers = _create_authenticated_user(client, db)

    response = client.put(
        f"{settings.API_V1_STR}/users/me/interests",
        headers=headers,
        json={"categories": [], "tags": [], "preferred_sources": ["OpenAI", 42]},
    )

    assert response.status_code == 422
    detail = response.json()["detail"]
    assert detail[0]["type"] == "string_type"
    assert detail[0]["loc"] == ["body", "preferred_sources", 1]


def test_read_interests_filters_retired_sources(
    client: TestClient,
    db: Session,
) -> None:
    """Stored names no longer in SOURCES are hidden from the read path.

    Belt-and-braces with the write-path filter: the frontend never sees a
    name it would only echo back, so stale rows stop propagating even
    before the pruning migration runs.
    """
    user, headers = _create_authenticated_user(client, db)
    # Write through CRUD to bypass the API-layer validator — this is the
    # shape a pre-existing production row has.
    crud.set_interests(
        session=db,
        user_id=user.id,
        categories=[],
        tags=[],
        preferred_sources=[RETIRED_SOURCE, "OpenAI"],
    )

    response = client.get(
        f"{settings.API_V1_STR}/users/me/interests",
        headers=headers,
    )

    assert response.status_code == 200
    assert response.json()["preferred_sources"] == ["OpenAI"]


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


def test_update_interests_drops_source_with_wrong_case(
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

    assert response.status_code == 200
    assert response.json()["preferred_sources"] == []
