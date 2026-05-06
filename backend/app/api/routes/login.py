import uuid
from datetime import timedelta
from typing import Annotated, Any, NoReturn

import jwt
from fastapi import APIRouter, Cookie, Depends, HTTPException, Response
from fastapi.responses import HTMLResponse
from fastapi.security import OAuth2PasswordRequestForm
from sqlmodel import Session

from app import crud
from app.api.deps import CurrentUser, SessionDep, get_current_active_superuser
from app.core import security
from app.core.config import settings
from app.core.cookies import (
    REFRESH_COOKIE_NAME,
    clear_auth_cookies,
    set_access_cookie,
    set_logged_in_marker,
    set_refresh_cookie,
)
from app.crud.refresh_session import (
    mark_refresh_session_used,
    refresh_token_matches_previous,
    revoke_refresh_session,
    revoke_refresh_sessions_for_user,
    rotate_refresh_session,
)
from app.models import User
from app.models.base import get_datetime_utc
from app.schemas import Message, NewPassword, Token, UserPublic, UserUpdate
from app.utils import (
    generate_password_reset_token,
    generate_reset_password_email,
    send_email,
    verify_password_reset_token,
)

router = APIRouter(tags=["login"])


class InvalidRefreshTokenError(ValueError):
    pass


def _refresh_ttl() -> timedelta:
    return timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)


def _issue_access_cookie(response: Response, user_id: Any) -> str:
    access_ttl = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = security.create_access_token(user_id, expires_delta=access_ttl)
    set_access_cookie(response, access_token, int(access_ttl.total_seconds()))
    return access_token


def _set_logged_in_marker(response: Response) -> None:
    refresh_ttl = _refresh_ttl()
    set_logged_in_marker(response, int(refresh_ttl.total_seconds()))


def _raise_refresh_unauthorized(response: Response, detail: str) -> NoReturn:
    clear_auth_cookies(response)
    raise HTTPException(status_code=401, detail=detail)


def _parse_refresh_payload(payload: dict[str, Any]) -> tuple[uuid.UUID, uuid.UUID, str]:
    subject = payload.get("sub")
    session_id = payload.get("sid")
    token_id = payload.get("jti")
    if not isinstance(subject, str) or not isinstance(session_id, str):
        raise InvalidRefreshTokenError
    if not isinstance(token_id, str) or not token_id:
        raise InvalidRefreshTokenError
    try:
        return uuid.UUID(subject), uuid.UUID(session_id), token_id
    except ValueError:
        raise InvalidRefreshTokenError


def _issue_session(response: Response, session: Session, user_id: uuid.UUID) -> str:
    """Mint access + refresh tokens, set all three auth cookies, return access token.

    Returning the access token lets the test suite continue using Bearer auth
    against endpoints other than the login flow. The frontend never reads it.
    """
    refresh_ttl = _refresh_ttl()
    refresh_token_id = security.generate_refresh_token_id()
    db_refresh_session = crud.create_refresh_session(
        session=session,
        user_id=user_id,
        token_hash=crud.hash_refresh_token_id(refresh_token_id),
        expires_at=get_datetime_utc() + refresh_ttl,
    )
    refresh_token = security.create_refresh_token(
        user_id,
        expires_delta=refresh_ttl,
        session_id=db_refresh_session.id,
        token_id=refresh_token_id,
    )
    session.commit()

    access_token = _issue_access_cookie(response, user_id)
    set_refresh_cookie(response, refresh_token, int(refresh_ttl.total_seconds()))
    _set_logged_in_marker(response)

    return access_token


@router.post("/login/access-token")
def login_access_token(
    response: Response,
    session: SessionDep,
    form_data: Annotated[OAuth2PasswordRequestForm, Depends()],
) -> Token:
    """Authenticate a user and start a cookie-backed session.

    Sets three cookies (access, refresh, is_logged_in marker) and also
    returns the access token in the response body. The body is for the
    test suite and isn't used by the frontend — production traffic
    authenticates entirely via the cookies.
    """
    user = crud.authenticate(
        session=session, email=form_data.username, password=form_data.password
    )
    if not user:
        raise HTTPException(status_code=400, detail="Incorrect email or password")
    if not user.is_active:
        raise HTTPException(status_code=400, detail="Inactive user")

    access_token = _issue_session(response, session, user.id)
    return Token(access_token=access_token)


@router.post("/login/refresh")
def refresh_session(
    response: Response,
    session: SessionDep,
    refresh_token: Annotated[str | None, Cookie(alias=REFRESH_COOKIE_NAME)] = None,
) -> Message:
    """Mint a new access token using the refresh cookie.

    Refresh tokens are DB-backed and rotated on each successful refresh. A
    short previous-token grace window avoids logging users out when two browser
    tabs refresh at almost the same time.
    """
    if not refresh_token:
        _raise_refresh_unauthorized(response, "No refresh token")
    try:
        payload = security.decode_token(refresh_token, expected_type="refresh")
        user_id, refresh_session_id, token_id = _parse_refresh_payload(payload)
    except (jwt.InvalidTokenError, InvalidRefreshTokenError):
        _raise_refresh_unauthorized(response, "Invalid refresh token")

    now = get_datetime_utc()
    token_hash = crud.hash_refresh_token_id(token_id)
    db_refresh_session = crud.get_refresh_session_for_update(
        session=session, session_id=refresh_session_id
    )
    if (
        db_refresh_session is None
        or db_refresh_session.user_id != user_id
        or not crud.refresh_session_is_active(
            refresh_session=db_refresh_session, now=now
        )
    ):
        _raise_refresh_unauthorized(response, "Invalid refresh token")

    user = session.get(User, user_id)
    if not user or not user.is_active:
        _raise_refresh_unauthorized(response, "Invalid refresh token")

    if db_refresh_session.token_hash == token_hash:
        refresh_ttl = _refresh_ttl()
        new_token_id = security.generate_refresh_token_id()
        new_token_hash = crud.hash_refresh_token_id(new_token_id)
        new_refresh_token = security.create_refresh_token(
            user_id,
            expires_delta=refresh_ttl,
            session_id=db_refresh_session.id,
            token_id=new_token_id,
        )
        rotate_refresh_session(
            refresh_session=db_refresh_session,
            old_token_hash=token_hash,
            new_token_hash=new_token_hash,
            expires_at=now + refresh_ttl,
            now=now,
        )
        session.add(db_refresh_session)
        session.commit()

        _issue_access_cookie(response, user_id)
        set_refresh_cookie(
            response, new_refresh_token, int(refresh_ttl.total_seconds())
        )
        _set_logged_in_marker(response)
        return Message(message="Session refreshed")

    if refresh_token_matches_previous(
        refresh_session=db_refresh_session, token_hash=token_hash, now=now
    ):
        mark_refresh_session_used(refresh_session=db_refresh_session, now=now)
        session.add(db_refresh_session)
        session.commit()

        _issue_access_cookie(response, user_id)
        _set_logged_in_marker(response)
        return Message(message="Session refreshed")

    revoke_refresh_session(refresh_session=db_refresh_session, now=now)
    session.add(db_refresh_session)
    session.commit()
    _raise_refresh_unauthorized(response, "Invalid refresh token")


def _revoke_refresh_session_from_cookie(session: Session, refresh_token: str) -> None:
    try:
        payload = security.decode_token(refresh_token, expected_type="refresh")
        user_id, refresh_session_id, token_id = _parse_refresh_payload(payload)
    except (jwt.InvalidTokenError, InvalidRefreshTokenError):
        return

    db_refresh_session = crud.get_refresh_session_for_update(
        session=session, session_id=refresh_session_id
    )
    if db_refresh_session is None or db_refresh_session.user_id != user_id:
        return

    token_hash = crud.hash_refresh_token_id(token_id)
    now = get_datetime_utc()
    if (
        db_refresh_session.token_hash != token_hash
        and not refresh_token_matches_previous(
            refresh_session=db_refresh_session, token_hash=token_hash, now=now
        )
    ):
        return

    revoke_refresh_session(refresh_session=db_refresh_session, now=now)
    session.add(db_refresh_session)
    session.commit()


@router.post("/login/logout")
def logout(
    response: Response,
    session: SessionDep,
    refresh_token: Annotated[str | None, Cookie(alias=REFRESH_COOKIE_NAME)] = None,
) -> Message:
    """Revoke the current refresh session and clear all auth cookies."""
    if refresh_token:
        _revoke_refresh_session_from_cookie(session, refresh_token)
    clear_auth_cookies(response)
    return Message(message="Logged out")


@router.post("/login/test-token", response_model=UserPublic)
def test_token(current_user: CurrentUser) -> Any:
    """
    Test access token
    """
    return current_user


@router.post("/password-recovery/{email}")
def recover_password(email: str, session: SessionDep) -> Message:
    """
    Password Recovery
    """
    user = crud.get_user_by_email(session=session, email=email)

    # Always return the same response to prevent email enumeration attacks
    # Only send email if user actually exists
    if user:
        password_reset_token = generate_password_reset_token(email=email)
        email_data = generate_reset_password_email(
            email_to=user.email, email=email, token=password_reset_token
        )
        send_email(
            email_to=user.email,
            subject=email_data.subject,
            html_content=email_data.html_content,
        )
    return Message(
        message="If that email is registered, we sent a password recovery link"
    )


@router.post("/reset-password/")
def reset_password(session: SessionDep, body: NewPassword) -> Message:
    """
    Reset password
    """
    email = verify_password_reset_token(token=body.token)
    if not email:
        raise HTTPException(status_code=400, detail="Invalid token")
    user = crud.get_user_by_email(session=session, email=email)
    if not user:
        # Don't reveal that the user doesn't exist - use same error as invalid token
        raise HTTPException(status_code=400, detail="Invalid token")
    elif not user.is_active:
        raise HTTPException(status_code=400, detail="Inactive user")
    user_in_update = UserUpdate(password=body.new_password)
    crud.update_user(
        session=session,
        db_user=user,
        user_in=user_in_update,
    )
    revoke_refresh_sessions_for_user(session=session, user_id=user.id)
    session.commit()
    return Message(message="Password updated successfully")


@router.post(
    "/password-recovery-html-content/{email}",
    dependencies=[Depends(get_current_active_superuser)],
    response_class=HTMLResponse,
)
def recover_password_html_content(email: str, session: SessionDep) -> Any:
    """
    HTML Content for Password Recovery
    """
    user = crud.get_user_by_email(session=session, email=email)

    if not user:
        raise HTTPException(
            status_code=404,
            detail="The user with this username does not exist in the system.",
        )
    password_reset_token = generate_password_reset_token(email=email)
    email_data = generate_reset_password_email(
        email_to=user.email, email=email, token=password_reset_token
    )

    return HTMLResponse(
        content=email_data.html_content, headers={"subject:": email_data.subject}
    )
