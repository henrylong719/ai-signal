from datetime import timedelta
from typing import Annotated, Any

import jwt
from fastapi import APIRouter, Cookie, Depends, HTTPException, Response
from fastapi.responses import HTMLResponse
from fastapi.security import OAuth2PasswordRequestForm

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
from app.schemas import Message, NewPassword, Token, UserPublic, UserUpdate
from app.utils import (
    generate_password_reset_token,
    generate_reset_password_email,
    send_email,
    verify_password_reset_token,
)

router = APIRouter(tags=["login"])


def _issue_session(response: Response, user_id: Any) -> str:
    """Mint access + refresh tokens, set all three auth cookies, return access token.

    Returning the access token lets the test suite continue using Bearer auth
    against endpoints other than the login flow. The frontend never reads it.
    """
    access_ttl = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    refresh_ttl = timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)

    access_token = security.create_access_token(user_id, expires_delta=access_ttl)
    refresh_token = security.create_refresh_token(user_id, expires_delta=refresh_ttl)

    set_access_cookie(response, access_token, int(access_ttl.total_seconds()))
    set_refresh_cookie(response, refresh_token, int(refresh_ttl.total_seconds()))
    # Marker matches the refresh TTL — the user "stays logged in" for as long
    # as their refresh token is valid, even if the access token expires often.
    set_logged_in_marker(response, int(refresh_ttl.total_seconds()))

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

    access_token = _issue_session(response, user.id)
    return Token(access_token=access_token)


@router.post("/login/refresh")
def refresh_session(
    response: Response,
    refresh_token: Annotated[str | None, Cookie(alias=REFRESH_COOKIE_NAME)] = None,
) -> Message:
    """Mint a new access token using the refresh cookie.

    Rotates the refresh token too: each refresh issues a fresh refresh
    cookie alongside the access cookie. This means a stolen refresh token
    is single-use — the next legitimate refresh invalidates it (because
    JWTs are stateless we can't actually invalidate the old one, but in
    practice the legitimate user's next refresh will overwrite the cookie
    and any subsequent attacker use will at least show stale activity).
    Production-grade rotation requires server-side refresh-token tracking,
    which we'd add via Redis if the project ever needed it.
    """
    if not refresh_token:
        raise HTTPException(status_code=401, detail="No refresh token")
    try:
        payload = security.decode_token(refresh_token, expected_type="refresh")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid refresh token")

    subject = payload.get("sub")
    if not subject:
        raise HTTPException(status_code=401, detail="Invalid refresh token")

    _issue_session(response, subject)
    return Message(message="Session refreshed")


@router.post("/login/logout")
def logout(response: Response) -> Message:
    """Clear all auth cookies. No-op if the user wasn't logged in."""
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
