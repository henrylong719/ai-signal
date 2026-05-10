import uuid
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Response
from sqlmodel import col, func, select

from app import crud
from app.api.deps import (
    CurrentUser,
    SessionDep,
    get_current_active_superuser,
)
from app.api.routes.login import issue_session
from app.core.config import settings
from app.core.security import get_password_hash, verify_password
from app.models import OAuthAccount, User
from app.models.base import get_datetime_utc
from app.schemas import (
    DigestPreferencesUpdate,
    Message,
    OAuthAccountPublic,
    OAuthAccountsPublic,
    OnboardingComplete,
    UpdatePassword,
    UserCreate,
    UserPublic,
    UserRegister,
    UsersPublic,
    UserUpdate,
    UserUpdateMe,
)
from app.services.email import send_new_account_email

router = APIRouter(prefix="/users", tags=["users"])


@router.get(
    "/",
    dependencies=[Depends(get_current_active_superuser)],
    response_model=UsersPublic,
)
def read_users(session: SessionDep, skip: int = 0, limit: int = 100) -> Any:
    """
    Retrieve users.
    """

    count_statement = select(func.count()).select_from(User)
    count = session.exec(count_statement).one()

    statement = (
        select(User).order_by(col(User.created_at).desc()).offset(skip).limit(limit)
    )
    users = session.exec(statement).all()

    users_public = [UserPublic.model_validate(user) for user in users]
    return UsersPublic(data=users_public, count=count)


@router.post(
    "/", dependencies=[Depends(get_current_active_superuser)], response_model=UserPublic
)
def create_user(*, session: SessionDep, user_in: UserCreate) -> Any:
    """
    Create new user.
    """
    user = crud.get_user_by_email(session=session, email=user_in.email)
    if user:
        raise HTTPException(
            status_code=400,
            detail="The user with this email already exists in the system.",
        )

    user = crud.create_user(session=session, user_create=user_in)
    if settings.emails_enabled and user_in.email:
        # Resend errors are logged inside the service; we don't fail
        # account creation just because the welcome email bounced.
        send_new_account_email(
            email_to=user_in.email,
            username=user_in.email,
            password=user_in.password,
        )
    return user


@router.patch("/me", response_model=UserPublic)
def update_user_me(
    *, session: SessionDep, user_in: UserUpdateMe, current_user: CurrentUser
) -> Any:
    """
    Update own user.
    """

    if user_in.email:
        existing_user = crud.get_user_by_email(session=session, email=user_in.email)
        if existing_user and existing_user.id != current_user.id:
            raise HTTPException(
                status_code=409, detail="User with this email already exists"
            )
    user_data = user_in.model_dump(exclude_unset=True)
    current_user.sqlmodel_update(user_data)
    session.add(current_user)
    session.commit()
    session.refresh(current_user)
    return current_user


@router.patch("/me/password", response_model=Message)
def update_password_me(
    *, session: SessionDep, body: UpdatePassword, current_user: CurrentUser
) -> Any:
    """
    Update own password.
    """
    verified, _ = verify_password(body.current_password, current_user.hashed_password)
    if not verified:
        raise HTTPException(status_code=400, detail="Incorrect password")
    if body.current_password == body.new_password:
        raise HTTPException(
            status_code=400,
            detail="New password cannot be the same as the current one",
        )
    hashed_password = get_password_hash(body.new_password)
    current_user.hashed_password = hashed_password
    current_user.has_password = True
    session.add(current_user)
    crud.revoke_refresh_sessions_for_user(session=session, user_id=current_user.id)
    session.commit()
    return Message(message="Password updated successfully")


@router.get("/me", response_model=UserPublic)
def read_user_me(current_user: CurrentUser) -> Any:
    """
    Get current user.
    """
    return current_user


@router.put("/me/onboarding", response_model=UserPublic)
def complete_onboarding(
    *,
    session: SessionDep,
    body: OnboardingComplete,
    current_user: CurrentUser,
) -> Any:
    """Mark first-run onboarding complete and persist captured preferences.

    The frontend calls this from the final step of the welcome modal
    once the user has picked their topics/sources. Setting
    ``onboarded_at`` here is what stops the modal from re-opening on
    the next sign-in. Repeated calls (user navigates back, picks a
    different digest opt-in, finishes again) overwrite cleanly.

    The actual interest data (categories, tags, preferred sources) is
    written through the existing /users/me/interests endpoint earlier
    in the flow — this endpoint only owns the metadata fields that
    didn't have a home before (timezone, digest opt-in, completion
    timestamp).
    """
    if body.timezone is not None:
        current_user.timezone = body.timezone
    current_user.daily_digest_enabled = body.daily_digest_enabled
    if current_user.onboarded_at is None:
        current_user.onboarded_at = get_datetime_utc()
    session.add(current_user)
    session.commit()
    session.refresh(current_user)
    return current_user


@router.put("/me/digest-preferences", response_model=UserPublic)
def update_digest_preferences(
    *,
    session: SessionDep,
    body: DigestPreferencesUpdate,
    current_user: CurrentUser,
) -> Any:
    """Update digest opt-in flag and/or cached timezone.

    Independent of the onboarding flow so the user can change their
    mind from the settings page after first run. Both fields are
    optional; omitted fields keep their current value.
    """
    if body.daily_digest_enabled is not None:
        # When disabling, reset the watermark so re-enabling on the
        # same calendar day still triggers a send (the loop's
        # idempotency check would otherwise skip "already sent today").
        if current_user.daily_digest_enabled and not body.daily_digest_enabled:
            current_user.last_digest_sent_at = get_datetime_utc()
        current_user.daily_digest_enabled = body.daily_digest_enabled
    if body.timezone is not None:
        current_user.timezone = body.timezone
    session.add(current_user)
    session.commit()
    session.refresh(current_user)
    return current_user


@router.get("/me/oauth-accounts", response_model=OAuthAccountsPublic)
def read_user_oauth_accounts(
    session: SessionDep,
    current_user: CurrentUser,
) -> Any:
    """
    List social sign-in providers connected to the current user.
    """
    statement = (
        select(OAuthAccount)
        .where(OAuthAccount.user_id == current_user.id)
        .order_by(col(OAuthAccount.created_at))
    )
    accounts = session.exec(statement).all()
    return OAuthAccountsPublic(
        data=[OAuthAccountPublic.model_validate(account) for account in accounts]
    )


@router.delete("/me", response_model=Message)
def delete_user_me(session: SessionDep, current_user: CurrentUser) -> Any:
    """
    Delete own user.
    """
    if current_user.is_superuser:
        raise HTTPException(
            status_code=403, detail="Super users are not allowed to delete themselves"
        )
    crud.revoke_refresh_sessions_for_user(session=session, user_id=current_user.id)
    session.delete(current_user)
    session.commit()
    return Message(message="User deleted successfully")


@router.post("/signup", response_model=UserPublic)
def register_user(
    session: SessionDep, user_in: UserRegister, response: Response
) -> Any:
    """
    Create new user without the need to be logged in.

    Issues an auth session on success so a fresh signup lands the user
    inside the app without a separate login round-trip.
    """
    user = crud.get_user_by_email(session=session, email=user_in.email)
    if user:
        raise HTTPException(
            status_code=400,
            detail="The user with this email already exists in the system",
        )
    user_create = UserCreate.model_validate(user_in)
    user = crud.create_user(session=session, user_create=user_create)
    issue_session(response, session, user.id)
    return user


@router.get("/{user_id}", response_model=UserPublic)
def read_user_by_id(
    user_id: uuid.UUID, session: SessionDep, current_user: CurrentUser
) -> Any:
    """
    Get a specific user by id.
    """
    user = session.get(User, user_id)
    if user == current_user:
        return user
    if not current_user.is_superuser:
        raise HTTPException(
            status_code=403,
            detail="The user doesn't have enough privileges",
        )
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")
    return user


@router.patch(
    "/{user_id}",
    dependencies=[Depends(get_current_active_superuser)],
    response_model=UserPublic,
)
def update_user(
    *,
    session: SessionDep,
    user_id: uuid.UUID,
    user_in: UserUpdate,
) -> Any:
    """
    Update a user.
    """

    db_user = session.get(User, user_id)
    if not db_user:
        raise HTTPException(
            status_code=404,
            detail="The user with this id does not exist in the system",
        )
    if user_in.email:
        existing_user = crud.get_user_by_email(session=session, email=user_in.email)
        if existing_user and existing_user.id != user_id:
            raise HTTPException(
                status_code=409, detail="User with this email already exists"
            )

    db_user = crud.update_user(session=session, db_user=db_user, user_in=user_in)
    if user_in.password is not None:
        crud.revoke_refresh_sessions_for_user(session=session, user_id=db_user.id)
        session.commit()
    return db_user


@router.delete("/{user_id}", dependencies=[Depends(get_current_active_superuser)])
def delete_user(
    session: SessionDep, current_user: CurrentUser, user_id: uuid.UUID
) -> Message:
    """
    Delete a user.
    """
    user = session.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    if user == current_user:
        raise HTTPException(
            status_code=403, detail="Super users are not allowed to delete themselves"
        )
    crud.revoke_refresh_sessions_for_user(session=session, user_id=user_id)
    session.delete(user)
    session.commit()
    return Message(message="User deleted successfully")
