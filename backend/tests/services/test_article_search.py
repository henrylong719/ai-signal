from uuid import uuid4

import pytest

from app.models import Article
from app.services import article_search


def _article(title: str, source: str = "Source A") -> Article:
    return Article(
        id=uuid4(),
        url=f"https://example.com/{uuid4()}",
        title=title,
        source=source,
        excerpt="excerpt",
        category="models",
        tags=["models"],
    )


def test_latest_search_returns_empty_page_when_rerank_pool_is_empty(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(article_search.crud, "count_articles", lambda **_kwargs: 0)
    monkeypatch.setattr(article_search.crud, "get_articles", lambda **_kwargs: [])

    articles, count = article_search.search_articles(
        session=object(),  # type: ignore[arg-type]
        search=" ",
    )

    assert articles == []
    assert count == 0


def test_latest_search_deep_pagination_uses_chronological_tail(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    tail = [_article("Tail")]
    calls: list[dict] = []

    monkeypatch.setattr(article_search.crud, "count_articles", lambda **_kwargs: 12)

    def fake_get_articles(**kwargs):
        calls.append(kwargs)
        return tail

    monkeypatch.setattr(article_search.crud, "get_articles", fake_get_articles)
    monkeypatch.setattr(
        article_search,
        "_rerank_latest_pool",
        lambda **_kwargs: pytest.fail("deep pagination should not rerank"),
    )

    articles, count = article_search.search_articles(
        session=object(),  # type: ignore[arg-type]
        search=None,
        skip=article_search._LATEST_RERANK_POOL_SIZE,
        limit=1,
    )

    assert articles == tail
    assert count == 12
    assert calls[0]["skip"] == article_search._LATEST_RERANK_POOL_SIZE
    assert calls[0]["limit"] == 1


def test_search_falls_back_to_keyword_when_no_semantic_articles_exist(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    keyword_results = [_article("Keyword match")]

    monkeypatch.setattr(article_search, "embed_text", lambda _query: [0.1, 0.2])
    monkeypatch.setattr(
        article_search.crud,
        "count_semantic_search_articles",
        lambda **_kwargs: 0,
    )
    monkeypatch.setattr(article_search.crud, "count_articles", lambda **_kwargs: 1)
    monkeypatch.setattr(
        article_search.crud,
        "get_semantic_search_articles",
        lambda **_kwargs: pytest.fail("semantic query should be skipped"),
    )
    monkeypatch.setattr(
        article_search.crud,
        "get_articles",
        lambda **kwargs: keyword_results if kwargs["search"] == "agents" else [],
    )

    articles, count = article_search.search_articles(
        session=object(),  # type: ignore[arg-type]
        search=" agents ",
    )

    assert articles == keyword_results
    assert count == 1
