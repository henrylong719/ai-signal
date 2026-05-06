import uuid

from sqlmodel import Session, select

from app.models import OAuthAccount
from app.models.base import get_datetime_utc


def get_oauth_account(
    *,
    session: Session,
    provider: str,
    provider_user_id: str,
) -> OAuthAccount | None:
    statement = select(OAuthAccount).where(
        OAuthAccount.provider == provider,
        OAuthAccount.provider_user_id == provider_user_id,
    )
    return session.exec(statement).first()


def create_oauth_account(
    *,
    session: Session,
    user_id: uuid.UUID,
    provider: str,
    provider_user_id: str,
    email: str,
    email_verified: bool,
    display_name: str | None,
    avatar_url: str | None,
) -> OAuthAccount:
    account = OAuthAccount(
        user_id=user_id,
        provider=provider,
        provider_user_id=provider_user_id,
        email=email,
        email_verified=email_verified,
        display_name=display_name,
        avatar_url=avatar_url,
    )
    session.add(account)
    session.flush()
    return account


def update_oauth_account_profile(
    *,
    session: Session,
    account: OAuthAccount,
    email: str,
    email_verified: bool,
    display_name: str | None,
    avatar_url: str | None,
) -> OAuthAccount:
    account.email = email
    account.email_verified = email_verified
    account.display_name = display_name
    account.avatar_url = avatar_url
    account.updated_at = get_datetime_utc()
    session.add(account)
    session.flush()
    return account
