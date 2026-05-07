from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from typing import Any
from uuid import uuid4

import pytest

from app import crud as app_crud
from app.models import Article
from app.services import for_you
from app.services.recommender import UserProfile

NOW = datetime(2026, 5, 5, 12, 0, tzinfo=timezone.utc)


def _article(
    *,
    title: str,
    category: str = "models",
    source: str = "Example",
    tags: list[str] | None = None,
    age_days: int = 0,
) -> Article:
    return Article(
        id=uuid4(),
        url=f"https://example.com/{uuid4()}",
        title=title,
        source=source,
        excerpt="excerpt",
        category=category,
        tags=tags or [category],
        published_at=NOW - timedelta(days=age_days),
    )


def test_build_user_profile_aggregates_all_recommendation_signals(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    user_id = uuid4()
    saved_id = uuid4()
    dismissed_id = uuid4()
    interests = SimpleNamespace(
        categories=["agents"],
        tags=["tool-use"],
        preferred_sources=["OpenAI", "Anthropic"],
    )

    monkeypatch.setattr(
        app_crud,
        "get_interests",
        lambda *, session, user_id: interests,
    )
    monkeypatch.setattr(
        app_crud,
        "get_saved_signals",
        lambda *, session, user_id: (frozenset({"evals"}), frozenset({"OpenAI"})),
    )
    monkeypatch.setattr(
        app_crud,
        "get_clicked_signals",
        lambda *, session, user_id: (frozenset({"rag"}), frozenset({"LangChain"})),
    )
    monkeypatch.setattr(
        app_crud,
        "get_saved_article_ids",
        lambda *, session, user_id: [saved_id],
    )
    monkeypatch.setattr(
        app_crud,
        "get_event_article_ids",
        lambda *, session, user_id, event_type: [dismissed_id],
    )

    fake_session: Any = object()

    profile = for_you.build_user_profile(session=fake_session, user_id=user_id)

    assert profile == UserProfile(
        interest_categories=frozenset({"agents"}),
        interest_tags=frozenset({"tool-use"}),
        preferred_sources=frozenset({"OpenAI", "Anthropic"}),
        saved_tags=frozenset({"evals"}),
        saved_sources=frozenset({"OpenAI"}),
        clicked_tags=frozenset({"rag"}),
        clicked_sources=frozenset({"LangChain"}),
        saved_article_ids=frozenset({saved_id}),
        dismissed_article_ids=frozenset({dismissed_id}),
    )


def test_build_user_profile_treats_missing_interests_as_empty(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(app_crud, "get_interests", lambda **kwargs: None)
    monkeypatch.setattr(
        app_crud,
        "get_saved_signals",
        lambda **kwargs: (frozenset(), frozenset()),
    )
    monkeypatch.setattr(
        app_crud,
        "get_clicked_signals",
        lambda **kwargs: (frozenset(), frozenset()),
    )
    monkeypatch.setattr(app_crud, "get_saved_article_ids", lambda **kwargs: [])
    monkeypatch.setattr(app_crud, "get_event_article_ids", lambda **kwargs: [])

    fake_session: Any = object()

    profile = for_you.build_user_profile(session=fake_session, user_id=uuid4())

    assert profile == UserProfile()


def test_rank_for_you_excludes_negative_signals_and_paginates_after_scoring(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    user_id = uuid4()
    saved = _article(title="Saved", category="rag", tags=["rag"], age_days=0)
    dismissed = _article(title="Dismissed", category="rag", tags=["rag"], age_days=0)
    strongest = _article(title="Best match", category="rag", tags=["rag"], age_days=3)
    fresh = _article(title="Fresh but generic", category="other", tags=[], age_days=0)
    old_match = _article(title="Older match", category="rag", tags=["rag"], age_days=20)
    captured_excluded: set[object] = set()

    monkeypatch.setattr(
        for_you,
        "build_user_profile",
        lambda *, session, user_id: UserProfile(
            interest_categories=frozenset({"rag"}),
            interest_tags=frozenset({"rag"}),
            saved_article_ids=frozenset({saved.id}),
            dismissed_article_ids=frozenset({dismissed.id}),
        ),
    )

    def fake_candidates(**kwargs: object) -> list[Article]:
        excluded_ids = kwargs["excluded_ids"]
        limit = kwargs["limit"]
        assert isinstance(excluded_ids, set)
        captured_excluded.update(excluded_ids)
        assert limit == 200
        # Include saved/dismissed defensively; rank_for_you should filter them
        # even if the DB helper returned stale data.
        return [fresh, old_match, saved, dismissed, strongest]

    monkeypatch.setattr(
        app_crud,
        "get_recent_articles_excluding",
        fake_candidates,
    )
    monkeypatch.setattr(app_crud, "get_user_embedding", lambda **kwargs: None)
    monkeypatch.setattr(
        for_you,
        "compute_and_save_user_vector",
        lambda **kwargs: None,
    )

    fake_session: Any = object()

    items, total = for_you.rank_for_you(
        session=fake_session,
        user_id=user_id,
        skip=1,
        limit=1,
    )

    assert captured_excluded == {saved.id, dismissed.id}
    assert total == 3
    assert [item.scored.article.title for item in items] == ["Older match"]
    assert items[0].reason == "Because you follow RAG"
