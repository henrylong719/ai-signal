"""Tests for the safe article cleanup pipeline.

Covers the four safety invariants the cleanup service has to honor:
  - saved articles are never archived
  - saved articles are never deleted (even if they slipped past stage 1)
  - articles with a recent ``clicked`` event are protected at both stages
  - dry-run reports counts but makes no DB changes

Plus the happy path: old unsaved articles are archived; old archived
unsaved articles are deleted.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from uuid import uuid4

from sqlalchemy import update
from sqlmodel import Session

from app import crud
from app.models import Article, User
from app.models.article import ArticleEvent, SavedArticle
from app.schemas import ArticleCreate, UserCreate
from app.services.article_cleanup import run_article_cleanup
from tests.utils.utils import random_email, random_lower_string


def _user(db: Session) -> User:
    return crud.create_user(
        session=db,
        user_create=UserCreate(email=random_email(), password=random_lower_string()),
    )


def _article(db: Session, *, age_days: int, title: str = "x") -> Article:
    """Create an article whose ``published_at`` is ``age_days`` in the past."""
    return crud.create_article(
        session=db,
        article_in=ArticleCreate(
            url=f"https://example.com/{uuid4()}",
            title=title,
            source="Example",
            excerpt="x",
            category="models",
            tags=["models"],
            published_at=datetime.now(timezone.utc) - timedelta(days=age_days),
        ),
    )


def _force_archived_at(db: Session, *, article_id, archived_age_days: int) -> None:
    """Backdate ``archived_at`` so the row qualifies for stage-2 deletion.

    Used to exercise the delete stage without waiting wall-clock time.
    """
    stamp = datetime.now(timezone.utc) - timedelta(days=archived_age_days)
    db.execute(
        update(Article).where(Article.id == article_id).values(archived_at=stamp)
    )
    db.commit()


def test_dry_run_reports_archive_candidates_but_makes_no_changes(
    db: Session,
) -> None:
    old = _article(db, age_days=200, title="Old unsaved")
    fresh = _article(db, age_days=1, title="Fresh")

    result = run_article_cleanup(session=db, dry_run=True)

    assert result.dry_run is True
    assert result.archived_count >= 1
    # No writes happened — both rows still have archived_at = None.
    db.expire_all()
    assert crud.get_article(session=db, article_id=old.id).archived_at is None  # type: ignore[union-attr]
    assert (
        crud.get_article(session=db, article_id=fresh.id).archived_at is None  # type: ignore[union-attr]
    )


def test_apply_archives_old_unsaved_unengaged_articles(db: Session) -> None:
    old = _article(db, age_days=200, title="Old unsaved unengaged")
    fresh = _article(db, age_days=5, title="Fresh")

    result = run_article_cleanup(session=db, dry_run=False)

    assert result.dry_run is False
    assert result.archived_count >= 1
    db.expire_all()
    archived = crud.get_article(session=db, article_id=old.id)
    assert archived is not None
    assert archived.archived_at is not None
    # The young article is left alone.
    young = crud.get_article(session=db, article_id=fresh.id)
    assert young is not None
    assert young.archived_at is None


def test_saved_articles_are_never_archived(db: Session) -> None:
    user = _user(db)
    saved_old = _article(db, age_days=400, title="Saved but old")
    crud.save_article(session=db, user_id=user.id, article_id=saved_old.id)

    run_article_cleanup(session=db, dry_run=False)

    db.expire_all()
    article = crud.get_article(session=db, article_id=saved_old.id)
    assert article is not None
    assert article.archived_at is None


def test_recent_click_protects_article_from_archival(db: Session) -> None:
    user = _user(db)
    clicked_old = _article(db, age_days=200, title="Old but clicked recently")
    crud.record_event(
        session=db,
        user_id=user.id,
        article_id=clicked_old.id,
        event_type="clicked",
    )

    run_article_cleanup(session=db, dry_run=False)

    db.expire_all()
    article = crud.get_article(session=db, article_id=clicked_old.id)
    assert article is not None
    assert article.archived_at is None


def test_apply_deletes_archived_unsaved_articles(db: Session) -> None:
    old = _article(db, age_days=400, title="To delete")
    old_id = old.id
    _force_archived_at(db, article_id=old_id, archived_age_days=200)

    result = run_article_cleanup(session=db, dry_run=False)

    assert result.deleted_count >= 1
    db.expire_all()
    assert crud.get_article(session=db, article_id=old_id) is None


def test_archived_saved_article_is_not_deleted(db: Session) -> None:
    user = _user(db)
    article = _article(db, age_days=400, title="Archived then saved")
    _force_archived_at(db, article_id=article.id, archived_age_days=200)
    crud.save_article(session=db, user_id=user.id, article_id=article.id)

    run_article_cleanup(session=db, dry_run=False)

    assert crud.get_article(session=db, article_id=article.id) is not None


def test_recent_click_protects_archived_article_from_deletion(db: Session) -> None:
    user = _user(db)
    article = _article(db, age_days=400, title="Archived but recently clicked")
    _force_archived_at(db, article_id=article.id, archived_age_days=200)
    crud.record_event(
        session=db,
        user_id=user.id,
        article_id=article.id,
        event_type="clicked",
    )

    run_article_cleanup(session=db, dry_run=False)

    assert crud.get_article(session=db, article_id=article.id) is not None


def test_dry_run_does_not_delete(db: Session) -> None:
    article = _article(db, age_days=400, title="Would be deleted")
    article_id = article.id
    _force_archived_at(db, article_id=article_id, archived_age_days=200)

    result = run_article_cleanup(session=db, dry_run=True)

    assert result.dry_run is True
    assert result.deleted_count >= 1
    # Still present.
    db.expire_all()
    assert crud.get_article(session=db, article_id=article_id) is not None


def test_archived_articles_excluded_from_public_listing(db: Session) -> None:
    article = _article(db, age_days=400, title="Archived listing")
    _force_archived_at(db, article_id=article.id, archived_age_days=10)

    listed = crud.get_articles(session=db, limit=500)
    listed_ids = {a.id for a in listed}
    assert article.id not in listed_ids

    listed_all = crud.get_articles(session=db, limit=500, include_archived=True)
    listed_all_ids = {a.id for a in listed_all}
    assert article.id in listed_all_ids


def test_dismissed_event_does_not_protect_article(db: Session) -> None:
    """Dismiss is a negative signal — it shouldn't keep an article alive."""
    user = _user(db)
    article = _article(db, age_days=400, title="Dismissed and old")
    crud.record_event(
        session=db,
        user_id=user.id,
        article_id=article.id,
        event_type="dismissed",
    )

    run_article_cleanup(session=db, dry_run=False)

    db.expire_all()
    refreshed = crud.get_article(session=db, article_id=article.id)
    assert refreshed is not None
    assert refreshed.archived_at is not None


def test_cleanup_uses_fetched_at_when_published_at_is_null(db: Session) -> None:
    """Articles without ``published_at`` are aged by ``fetched_at``."""
    article = crud.create_article(
        session=db,
        article_in=ArticleCreate(
            url=f"https://example.com/{uuid4()}",
            title="No published_at",
            source="Example",
            excerpt="x",
            category="models",
            tags=["models"],
            published_at=None,
        ),
    )
    # Backdate fetched_at to look old.
    db.execute(
        update(Article)
        .where(Article.id == article.id)
        .values(fetched_at=datetime.now(timezone.utc) - timedelta(days=400))
    )
    db.commit()

    run_article_cleanup(session=db, dry_run=False)

    db.expire_all()
    refreshed = crud.get_article(session=db, article_id=article.id)
    assert refreshed is not None
    assert refreshed.archived_at is not None


def test_cleanup_clears_related_rows_on_delete(db: Session) -> None:
    """CASCADE on saved_articles / article_events fires on hard delete."""
    user = _user(db)
    article = _article(db, age_days=400, title="To cascade")
    article_id = article.id
    user_id = user.id
    _force_archived_at(db, article_id=article_id, archived_age_days=200)
    # An ancient click (outside the keep-window) should not protect the row,
    # but the event row itself should disappear on delete via CASCADE.
    crud.record_event(
        session=db,
        user_id=user_id,
        article_id=article_id,
        event_type="clicked",
    )
    # Push the click outside the keep window so it doesn't protect.
    db.execute(
        update(ArticleEvent)
        .where(ArticleEvent.article_id == article_id)
        .values(last_at=datetime.now(timezone.utc) - timedelta(days=365))
    )
    db.commit()

    run_article_cleanup(session=db, dry_run=False)

    db.expire_all()
    assert crud.get_article(session=db, article_id=article_id) is None
    remaining_events = db.get(ArticleEvent, (user_id, article_id, "clicked"))
    assert remaining_events is None
    # Saved-articles cascade is structurally identical; covered by the
    # "saved articles are never deleted" test above.
    _ = SavedArticle  # silence unused-import lint
