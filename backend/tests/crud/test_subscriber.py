"""CRUD tests for digest subscribers."""

from __future__ import annotations

from sqlmodel import Session

from app import crud
from app.models.base import get_datetime_utc
from app.schemas import UserCreate
from tests.utils.utils import random_email


def test_upsert_creates_active_subscriber(db: Session) -> None:
    email = random_email()
    subscriber, created = crud.upsert_subscriber(session=db, email=email)
    assert created is True
    assert subscriber.is_active is True
    assert subscriber.last_digest_sent_at is None


def test_upsert_reactivates_existing(db: Session) -> None:
    email = random_email()
    first, _ = crud.upsert_subscriber(session=db, email=email)
    crud.unsubscribe_subscriber(session=db, subscriber_id=first.id)

    again, created = crud.upsert_subscriber(session=db, email=email)
    assert created is False
    assert again.id == first.id
    assert again.is_active is True


def test_unsubscribe_is_idempotent(db: Session) -> None:
    email = random_email()
    subscriber, _ = crud.upsert_subscriber(session=db, email=email)

    first = crud.unsubscribe_subscriber(session=db, subscriber_id=subscriber.id)
    assert first is not None
    assert first.is_active is False

    second = crud.unsubscribe_subscriber(session=db, subscriber_id=subscriber.id)
    assert second is not None
    assert second.is_active is False


def test_get_sendable_subscribers_excludes_unsubscribed(db: Session) -> None:
    active_email = random_email()
    inactive_email = random_email()
    active, _ = crud.upsert_subscriber(session=db, email=active_email)
    inactive, _ = crud.upsert_subscriber(session=db, email=inactive_email)
    crud.unsubscribe_subscriber(session=db, subscriber_id=inactive.id)

    sendable_ids = {s.id for s in crud.get_sendable_subscribers(session=db)}
    assert active.id in sendable_ids
    assert inactive.id not in sendable_ids


def test_mark_subscriber_digest_sent_stamps_watermark(db: Session) -> None:
    subscriber, _ = crud.upsert_subscriber(session=db, email=random_email())
    now = get_datetime_utc()
    crud.mark_subscriber_digest_sent(session=db, subscriber=subscriber, now=now)
    db.refresh(subscriber)
    assert subscriber.last_digest_sent_at is not None


def test_get_active_digest_user_emails_lowercased(db: Session) -> None:
    enabled_email = random_email()
    disabled_email = random_email()
    enabled = crud.create_user(
        session=db,
        user_create=UserCreate(email=enabled_email, password="password123"),
    )
    enabled.daily_digest_enabled = True
    db.add(enabled)
    # A user without the digest opt-in must not appear in the dedupe set.
    crud.create_user(
        session=db,
        user_create=UserCreate(email=disabled_email, password="password123"),
    )
    db.commit()

    emails = crud.get_active_digest_user_emails(session=db)
    assert enabled_email.lower() in emails
    assert disabled_email.lower() not in emails
