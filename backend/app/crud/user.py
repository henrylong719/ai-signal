from typing import Any

from sqlmodel import Session, col, func, select

from app.core.security import get_password_hash, verify_password
from app.models import User
from app.schemas import UserCreate, UserUpdate


def create_user(*, session: Session, user_create: UserCreate) -> User:
    db_obj = User.model_validate(
        user_create, update={"hashed_password": get_password_hash(user_create.password)}
    )
    session.add(db_obj)
    session.commit()
    session.refresh(db_obj)
    return db_obj


def update_user(*, session: Session, db_user: User, user_in: UserUpdate) -> Any:
    user_data = user_in.model_dump(exclude_unset=True)
    extra_data: dict[str, Any] = {}
    if "password" in user_data:
        password = user_data["password"]
        hashed_password = get_password_hash(password)
        extra_data["hashed_password"] = hashed_password
        extra_data["has_password"] = True
    db_user.sqlmodel_update(user_data, update=extra_data)
    session.add(db_user)
    session.commit()
    session.refresh(db_user)
    return db_user


def get_active_digest_user_emails(*, session: Session) -> set[str]:
    """Lowercased emails of active, digest-enabled users.

    The subscriber send loop uses this to skip addresses that already
    receive the personalized user digest — one morning email per person,
    not two.
    """
    statement = select(User.email).where(
        col(User.is_active).is_(True),
        col(User.daily_digest_enabled).is_(True),
    )
    return {email.lower() for email in session.exec(statement).all()}


def get_user_by_email(*, session: Session, email: str) -> User | None:
    # Case-insensitive: new rows are stored lowercase (schema validators),
    # but rows created before normalization — and login forms, where the
    # user types their email freehand — can carry any casing.
    statement = select(User).where(
        func.lower(col(User.email)) == email.strip().lower()
    )
    session_user = session.exec(statement).first()
    return session_user


# Dummy hash to use for timing attack prevention when user is not found.
# This is an Argon2 hash of a random password, used to ensure constant-time comparison.
DUMMY_HASH = "$argon2id$v=19$m=65536,t=3,p=4$MjQyZWE1MzBjYjJlZTI0Yw$YTU4NGM5ZTZmYjE2NzZlZjY0ZWY3ZGRkY2U2OWFjNjk"


def authenticate(*, session: Session, email: str, password: str) -> User | None:
    db_user = get_user_by_email(session=session, email=email)
    if not db_user:
        # Prevent timing attacks by running password verification even when the
        # user does not exist.
        verify_password(password, DUMMY_HASH)
        return None
    if not db_user.has_password:
        verify_password(password, DUMMY_HASH)
        return None
    verified, updated_password_hash = verify_password(password, db_user.hashed_password)
    if not verified:
        return None
    if updated_password_hash:
        db_user.hashed_password = updated_password_hash
        session.add(db_user)
        session.commit()
        session.refresh(db_user)
    return db_user
