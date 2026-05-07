from datetime import datetime, timedelta, timezone
from uuid import uuid4

import pytest
from sqlmodel import Session

from app import crud
from app.models import Article, User
from app.models.article import ArticleEvent
from app.schemas import ArticleCreate, UserCreate
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

    assert crud.get_saved_signals(session=db, user_id=user.id) == (
        frozenset({"rag", "retrieval"}),
        frozenset({"Weaviate"}),
    )
    assert crud.get_clicked_signals(session=db, user_id=user.id) == (
        frozenset({"agents", "tool-use"}),
        frozenset({"LangChain"}),
    )


def test_get_recent_articles_excluding_filters_and_orders_candidates(
    db: Session,
) -> None:
    newest = _create_article(db, title="Newest", age_days=-30)
    excluded = _create_article(db, title="Excluded", age_days=-29)
    older = _create_article(db, title="Older", age_days=-28)

    result = crud.get_recent_articles_excluding(
        session=db,
        excluded_ids={excluded.id},
        limit=2,
    )

    result_ids = [article.id for article in result]
    assert excluded.id not in result_ids
    assert result_ids[:2] == [newest.id, older.id]
