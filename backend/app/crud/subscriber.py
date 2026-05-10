"""CRUD for digest subscribers."""

from sqlmodel import Session, select

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
