from datetime import datetime, timezone
from uuid import uuid4

import pytest

from app.models import Article
from app.schemas.source import Category
from app.services import digest, ranking
from app.services.digest import _build_sections, build_digest
from app.services.recommender import UserProfile

NOW = datetime(2026, 5, 5, 12, 0, tzinfo=timezone.utc)


def _article(
    *,
    title: str,
    source: str,
    category: Category = "models",
) -> Article:
    return Article(
        id=uuid4(),
        url=f"https://example.com/{uuid4()}",
        title=title,
        source=source,
        excerpt="excerpt",
        category=category,
        tags=[category],
        published_at=NOW,
    )


def test_top_stories_prefer_distinct_sources() -> None:
    articles = [
        _article(title="Highest ranked", source="Source A"),
        _article(title="Second from same source", source="Source A"),
        _article(title="Best from source B", source="Source B"),
        _article(title="Best from source C", source="Source C"),
    ]

    sections = _build_sections(articles, reasons={})

    assert [article.title for article in sections[0].articles] == [
        "Highest ranked",
        "Best from source B",
        "Best from source C",
    ]


def test_top_stories_fill_from_ranked_articles_when_sources_are_limited() -> None:
    articles = [
        _article(title="Highest ranked", source="Source A"),
        _article(title="Second from same source", source="Source A"),
        _article(title="Best from source B", source="Source B"),
        _article(title="Third from source A", source="Source A"),
    ]

    sections = _build_sections(articles, reasons={})

    assert [article.title for article in sections[0].articles] == [
        "Highest ranked",
        "Best from source B",
        "Second from same source",
    ]


def test_build_digest_widens_window_for_anonymous_users_when_today_is_empty(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fallback_article = _article(title="Fallback", source="Source A")
    calls = []

    def fake_get_articles_in_window_with_popularity(**kwargs):
        calls.append(kwargs)
        return [] if len(calls) == 1 else [(fallback_article, 0)]

    monkeypatch.setattr(
        digest.crud,
        "get_articles_in_window_with_popularity",
        fake_get_articles_in_window_with_popularity,
    )

    result = build_digest(session=object(), user_id=None, now=NOW)  # type: ignore[arg-type]

    assert result.is_personalized is False
    assert result.window_start == NOW - digest._FALLBACK_WINDOW
    assert [call["since"] for call in calls] == [
        NOW - digest._PRIMARY_WINDOW,
        NOW - digest._FALLBACK_WINDOW,
    ]
    assert result.sections[0].articles == [fallback_article]


def test_build_digest_personalizes_and_excludes_saved_and_dismissed_articles(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    user_id = uuid4()
    top_article = _article(
        title="Agents win",
        source="Source A",
        category="agents",
    )
    lower_article = _article(
        title="Other story",
        source="Source B",
        category="other",
    )
    saved_id = uuid4()
    dismissed_id = uuid4()
    profile = UserProfile(
        interest_categories=frozenset({"agents"}),
        saved_article_ids=frozenset({saved_id}),
        dismissed_article_ids=frozenset({dismissed_id}),
    )
    captured_excluded_ids: list[set] = []

    def fake_get_articles_in_window(**kwargs):
        captured_excluded_ids.append(kwargs["excluded_ids"])
        return [lower_article, top_article]

    monkeypatch.setattr(digest, "build_user_profile", lambda **_kwargs: profile)
    monkeypatch.setattr(ranking, "resolve_user_vector", lambda **_kwargs: None)
    monkeypatch.setattr(
        digest.crud, "get_articles_in_window", fake_get_articles_in_window
    )

    result = build_digest(session=object(), user_id=user_id, now=NOW)  # type: ignore[arg-type]

    assert result.is_personalized is True
    assert captured_excluded_ids == [{saved_id, dismissed_id}]
    assert [article.title for article in result.sections[0].articles] == [
        "Agents win",
        "Other story",
    ]
    assert result.sections[0].reasons[top_article.id] == "Because you follow Agents"
