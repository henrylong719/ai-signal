from datetime import datetime, timedelta, timezone
from uuid import uuid4

import pytest
from sqlmodel import Session, select

from app import crud
from app.models import Article, User
from app.models.article import ArticleEvent
from app.schemas import ArticleCreate, ArticleUpdate, UserCreate
from app.schemas.source import Category
from tests.utils.utils import random_email, random_lower_string

NOW = datetime(2026, 5, 5, 12, 0, tzinfo=timezone.utc)


def _create_user(db: Session) -> User:
    return crud.create_user(
        session=db,
        user_create=UserCreate(email=random_email(), password=random_lower_string()),
    )


def _create_article(
    db: Session,
    *,
    title: str,
    source: str = "Example",
    category: Category = "models",
    tags: list[str] | None = None,
    age_days: int = 0,
) -> Article:
    return crud.create_article(
        session=db,
        article_in=ArticleCreate(
            url=f"https://example.com/{uuid4()}",
            title=title,
            source=source,
            excerpt=f"{title} excerpt",
            category=category,
            tags=tags or [category],
            published_at=NOW - timedelta(days=age_days),
        ),
    )


def test_set_interests_normalizes_and_replaces_existing_row(db: Session) -> None:
    user = _create_user(db)

    created = crud.set_interests(
        session=db,
        user_id=user.id,
        categories=["rag", "models", "rag"],
        tags=[" RAG ", "Agents", "", "rag"],
        preferred_sources=["OpenAI", "Anthropic", "OpenAI"],
    )
    updated = crud.set_interests(
        session=db,
        user_id=user.id,
        categories=["agents"],
        tags=[" Tool Use ", "tool use", "Evals"],
        preferred_sources=["LangChain"],
    )

    assert created.user_id == user.id
    assert updated.user_id == user.id
    assert updated.categories == ["agents"]
    assert updated.tags == ["evals", "tool use"]
    assert updated.preferred_sources == ["LangChain"]


def test_record_event_inserts_then_increments_same_event(db: Session) -> None:
    user = _create_user(db)
    article = _create_article(db, title="Clicked")

    crud.record_event(
        session=db,
        user_id=user.id,
        article_id=article.id,
        event_type="clicked",
    )
    first = db.get(ArticleEvent, (user.id, article.id, "clicked"))
    assert first is not None
    first_seen_at = first.first_at

    crud.record_event(
        session=db,
        user_id=user.id,
        article_id=article.id,
        event_type="clicked",
    )
    db.expire_all()
    second = db.get(ArticleEvent, (user.id, article.id, "clicked"))

    assert second is not None
    assert second.count == 2
    assert second.first_at == first_seen_at
    assert second.last_at >= first_seen_at


def test_record_event_rejects_unknown_event_type(db: Session) -> None:
    user = _create_user(db)
    article = _create_article(db, title="Unknown event")

    with pytest.raises(ValueError, match="Unknown event_type"):
        crud.record_event(
            session=db,
            user_id=user.id,
            article_id=article.id,
            event_type="viewed",  # type: ignore[arg-type]
        )


def test_saved_and_clicked_signal_aggregates_return_distinct_tags_and_sources(
    db: Session,
) -> None:
    user = _create_user(db)
    saved = _create_article(
        db,
        title="Saved RAG",
        source="Weaviate",
        category="rag",
        tags=["rag", "retrieval", "rag"],
    )
    clicked = _create_article(
        db,
        title="Clicked Agents",
        source="LangChain",
        category="agents",
        tags=["agents", "tool-use"],
    )

    crud.save_article(session=db, user_id=user.id, article_id=saved.id)
    crud.record_event(
        session=db,
        user_id=user.id,
        article_id=clicked.id,
        event_type="clicked",
    )

    saved_tags, saved_sources = crud.get_saved_signals(session=db, user_id=user.id)
    clicked_tags, clicked_sources = crud.get_clicked_signals(
        session=db, user_id=user.id
    )

    # Tags and sources are weighted dicts (decay-weighted by recency
    # of interaction). Just-saved and just-clicked items have weight
    # ~1.0 modulo float drift from the seconds-old age. Assert key
    # membership and weight-near-1.0 separately so the test isn't
    # fragile to clock skew.
    assert saved_tags.keys() == {"rag", "retrieval"}
    assert saved_sources.keys() == {"Weaviate"}
    assert clicked_tags.keys() == {"agents", "tool-use"}
    assert clicked_sources.keys() == {"LangChain"}
    for w in (
        *saved_tags.values(),
        *saved_sources.values(),
        *clicked_tags.values(),
        *clicked_sources.values(),
    ):
        # Brand new interactions; decay should be effectively zero.
        assert 0.999 < w <= 1.0


def test_get_recent_articles_excluding_filters_and_orders_candidates(
    db: Session,
) -> None:
    # The suite intentionally shares one database session, so exclude rows
    # created by earlier tests and make this ordering assertion self-contained.
    preexisting_ids = set(db.exec(select(Article.id)).all())
    newest = _create_article(db, title="Newest", age_days=-30)
    excluded = _create_article(db, title="Excluded", age_days=-29)
    older = _create_article(db, title="Older", age_days=-28)

    result = crud.get_recent_articles_excluding(
        session=db,
        excluded_ids=preexisting_ids | {excluded.id},
        limit=2,
    )

    result_ids = [article.id for article in result]
    assert excluded.id not in result_ids
    assert result_ids[:2] == [newest.id, older.id]


def test_get_articles_by_ids_returns_empty_without_ids(db: Session) -> None:
    assert crud.get_articles_by_ids(session=db, article_ids=[]) == []


def test_update_and_delete_article(db: Session) -> None:
    article = _create_article(db, title="Original", source="Before")

    updated = crud.update_article(
        session=db,
        db_article=article,
        article_in=ArticleUpdate(title="Updated"),
    )

    assert updated.title == "Updated"
    assert updated.source == "Before"

    article_id = updated.id
    crud.delete_article(session=db, db_article=updated)

    assert crud.get_article(session=db, article_id=article_id) is None


def test_get_articles_with_saved_counts_filters_by_source_and_search(
    db: Session,
) -> None:
    user = _create_user(db)
    matching = _create_article(
        db,
        title="Literal 100% RAG_guide",
        source="Filtered Source",
        category="rag",
    )
    _create_article(
        db,
        title="Literal 100% RAG_guide",
        source="Other Source",
        category="rag",
    )
    crud.save_article(session=db, user_id=user.id, article_id=matching.id)

    result = crud.get_articles_with_saved_counts(
        session=db,
        source="Filtered Source",
        search="100% RAG_guide",
    )

    assert [(article.id, saved_count) for article, saved_count in result] == [
        (matching.id, 1)
    ]


def test_embedding_backfill_helpers_update_pending_articles(db: Session) -> None:
    vector = [0.1] * 384
    pending = _create_article(db, title="Needs embedding", age_days=-10)
    already_embedded = _create_article(db, title="Already embedded", age_days=-11)
    missing_id = uuid4()
    already_embedded.embedding = vector
    db.add(already_embedded)
    db.commit()

    pending_ids = {
        article.id
        # Do not let pending rows from earlier tests crowd this article out of
        # a small result page; pagination limits are covered elsewhere.
        for article in crud.get_pending_embedding_articles(session=db, limit=10_000)
    }

    assert pending.id in pending_ids
    assert already_embedded.id not in pending_ids
    assert crud.count_pending_embeddings(session=db) >= 1

    crud.update_article_embeddings(
        session=db,
        embeddings={pending.id: vector, missing_id: vector},
    )
    db.expire_all()

    updated = crud.get_article(session=db, article_id=pending.id)
    assert updated is not None
    assert list(updated.embedding) == pytest.approx(vector)


def test_get_articles_in_window_filters_excluded_ids_and_orders_by_recency(
    db: Session,
) -> None:
    since = NOW - timedelta(days=5)
    newest = _create_article(db, title="Window newest", age_days=-3)
    excluded = _create_article(db, title="Window excluded", age_days=-2)
    _create_article(db, title="Window too old", age_days=10)

    result = crud.get_articles_in_window(
        session=db,
        since=since,
        excluded_ids={excluded.id},
        limit=200,
    )

    result_ids = [article.id for article in result]
    assert newest.id in result_ids
    assert excluded.id not in result_ids
