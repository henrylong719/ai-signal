"""CRUD for digest subscribers."""

import uuid
from collections.abc import Sequence
from datetime import datetime

from sqlmodel import Session, col, select

from app.models.base import get_datetime_utc
from app.models.subscriber import DigestSubscriber


def get_subscriber_by_email(*, session: Session, email: str) -> DigestSubscriber | None:
    statement = select(DigestSubscriber).where(DigestSubscriber.email == email)
    return session.exec(statement).first()


def upsert_subscriber(*, session: Session, email: str) -> tuple[DigestSubscriber, bool]:
    """Insert a new subscriber or reactivate an existing one.

    Returns (subscriber, created) where ``created`` is True only when a row
    is inserted for the first time.
    """
    existing = get_subscriber_by_email(session=session, email=email)
    now = get_datetime_utc()

    if existing is None:
        subscriber = DigestSubscriber(
            email=email,
            is_active=True,
            created_at=now,
            updated_at=now,
        )
        session.add(subscriber)
        session.commit()
        session.refresh(subscriber)
        return subscriber, True

    if not existing.is_active:
        existing.is_active = True
    existing.updated_at = now
    session.add(existing)
    session.commit()
    session.refresh(existing)
    return existing, False


def unsubscribe_subscriber(
    *, session: Session, subscriber_id: uuid.UUID
) -> DigestSubscriber | None:
    """Deactivate a subscriber. Idempotent; returns None if the row is gone."""
    subscriber = session.get(DigestSubscriber, subscriber_id)
    if subscriber is None:
        return None
    if subscriber.is_active:
        subscriber.is_active = False
        subscriber.updated_at = get_datetime_utc()
        session.add(subscriber)
        session.commit()
        session.refresh(subscriber)
    return subscriber


def get_sendable_subscribers(*, session: Session) -> Sequence[DigestSubscriber]:
    """Active subscribers eligible for the digest (single opt-in)."""
    statement = select(DigestSubscriber).where(
        col(DigestSubscriber.is_active).is_(True)
    )
    return session.exec(statement).all()


def mark_subscriber_digest_sent(
    *, session: Session, subscriber: DigestSubscriber, now: datetime
) -> None:
    """Stamp the idempotency watermark after a successful send."""
    subscriber.last_digest_sent_at = now
    session.add(subscriber)
    session.commit()
