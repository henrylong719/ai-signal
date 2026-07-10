import uuid

from sqlmodel import Session, col, func, select

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


def user_has_verified_oauth_email(
    *,
    session: Session,
    user_id: uuid.UUID,
    email: str,
) -> bool:
    """True iff the user already has a provider-*verified* OAuth link for
    ``email``. This is what distinguishes an email a provider confirmed
    from one merely parked on the account row via a profile edit — only
    the former is safe to auto-link a new provider identity onto.
    """
    statement = select(OAuthAccount).where(
        OAuthAccount.user_id == user_id,
        func.lower(col(OAuthAccount.email)) == email.strip().lower(),
        col(OAuthAccount.email_verified).is_(True),
    )
    return session.exec(statement).first() is not None


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
