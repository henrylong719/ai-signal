import logging
import secrets
import uuid
from dataclasses import dataclass
from datetime import timedelta
from typing import Annotated, Any, NoReturn, cast
from urllib.parse import urlencode

import httpx
import jwt
from fastapi import APIRouter, Cookie, Depends, HTTPException, Request, Response
from fastapi.responses import HTMLResponse, RedirectResponse
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
logger = logging.getLogger(__name__)


OAUTH_STATE_COOKIE_NAME = "oauth_state"
OAUTH_STATE_MAX_AGE_SECONDS = 10 * 60
OAUTH_HTTP_TIMEOUT_SECONDS = 10.0


class InvalidRefreshTokenError(ValueError):
    pass


@dataclass(frozen=True)
class OAuthProviderConfig:
    authorize_url: str
    token_url: str
    scope: str
    client_id: str
    client_secret: str


@dataclass(frozen=True)
class OAuthIdentity:
    provider: str
    provider_user_id: str
    email: str
    email_verified: bool
    display_name: str | None
    avatar_url: str | None


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


def _oauth_cookie_secure() -> bool:
    return settings.ENVIRONMENT != "local"


def _frontend_redirect(path: str, params: dict[str, str] | None = None) -> str:
    base_url = settings.FRONTEND_HOST.rstrip("/")
    query = f"?{urlencode(params)}" if params else ""
    return f"{base_url}{path}{query}"


def _oauth_error_redirect(detail: str) -> RedirectResponse:
    return RedirectResponse(
        _frontend_redirect("/login", {"social_error": detail}),
        status_code=303,
    )


def _generic_oauth_error_message() -> str:
    return "We could not complete social sign-in. Please try again."


def _provider_error_message(error: str) -> str:
    if error == "access_denied":
        return "Social sign-in was canceled."
    return _generic_oauth_error_message()


def _oauth_failure_message(error: Exception) -> str:
    if isinstance(error, httpx.HTTPError):
        return _generic_oauth_error_message()
    if isinstance(error, ValueError) and str(error):
        return str(error)
    return _generic_oauth_error_message()


def _set_oauth_state_cookie(response: Response, state: str) -> None:
    response.set_cookie(
        key=OAUTH_STATE_COOKIE_NAME,
        value=state,
        max_age=OAUTH_STATE_MAX_AGE_SECONDS,
        path=f"{settings.API_V1_STR}/login",
        secure=_oauth_cookie_secure(),
        httponly=True,
        samesite="lax",
    )


def _clear_oauth_state_cookie(response: Response) -> None:
    response.delete_cookie(
        key=OAUTH_STATE_COOKIE_NAME,
        path=f"{settings.API_V1_STR}/login",
        secure=_oauth_cookie_secure(),
        httponly=True,
        samesite="lax",
    )


def _provider_config(provider: str) -> OAuthProviderConfig:
    if provider == "google":
        client_id = settings.GOOGLE_OAUTH_CLIENT_ID
        client_secret = settings.GOOGLE_OAUTH_CLIENT_SECRET
        if not client_id or not client_secret:
            raise HTTPException(
                status_code=503,
                detail="Google OAuth is not configured",
            )
        return OAuthProviderConfig(
            authorize_url="https://accounts.google.com/o/oauth2/v2/auth",
            token_url="https://oauth2.googleapis.com/token",
            scope="openid email profile",
            client_id=client_id,
            client_secret=client_secret,
        )

    if provider == "github":
        client_id = settings.GITHUB_OAUTH_CLIENT_ID
        client_secret = settings.GITHUB_OAUTH_CLIENT_SECRET
        if not client_id or not client_secret:
            raise HTTPException(
                status_code=503,
                detail="GitHub OAuth is not configured",
            )
        return OAuthProviderConfig(
            authorize_url="https://github.com/login/oauth/authorize",
            token_url="https://github.com/login/oauth/access_token",
            scope="read:user user:email",
            client_id=client_id,
            client_secret=client_secret,
        )

    raise HTTPException(status_code=404, detail="Unsupported OAuth provider")


def _callback_url(request: Request, provider: str) -> str:
    return str(request.url_for("oauth_callback", provider=provider))


def _exchange_oauth_code(
    *,
    client: httpx.Client,
    config: OAuthProviderConfig,
    code: str,
    redirect_uri: str,
) -> str:
    response = client.post(
        config.token_url,
        data={
            "client_id": config.client_id,
            "client_secret": config.client_secret,
            "code": code,
            "grant_type": "authorization_code",
            "redirect_uri": redirect_uri,
        },
        headers={"Accept": "application/json"},
    )
    response.raise_for_status()
    access_token = response.json().get("access_token")
    if not isinstance(access_token, str) or not access_token:
        raise ValueError("Provider did not return an access token")
    return access_token


def _bool_from_provider(value: object) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.lower() == "true"
    return False


def _google_identity(*, client: httpx.Client, access_token: str) -> OAuthIdentity:
    response = client.get(
        "https://openidconnect.googleapis.com/v1/userinfo",
        headers={"Authorization": f"Bearer {access_token}"},
    )
    response.raise_for_status()
    data = response.json()
    provider_user_id = data.get("sub")
    email = data.get("email")
    if not isinstance(provider_user_id, str) or not isinstance(email, str):
        raise ValueError("Google did not return the required identity fields")

    return OAuthIdentity(
        provider="google",
        provider_user_id=provider_user_id,
        email=email.lower(),
        email_verified=_bool_from_provider(data.get("email_verified")),
        display_name=data.get("name") if isinstance(data.get("name"), str) else None,
        avatar_url=(
            data.get("picture") if isinstance(data.get("picture"), str) else None
        ),
    )


def _github_email(emails: list[object]) -> tuple[str, bool] | None:
    fallback_email: str | None = None

    for item in emails:
        if not isinstance(item, dict):
            continue

        email_data = cast(dict[str, object], item)
        email = email_data.get("email")
        if not isinstance(email, str) or email_data.get("verified") is not True:
            continue

        if email_data.get("primary") is True:
            return email.lower(), True

        fallback_email = fallback_email or email

    if fallback_email is None:
        return None
    return fallback_email.lower(), True


def _github_identity(*, client: httpx.Client, access_token: str) -> OAuthIdentity:
    headers = {
        "Accept": "application/vnd.github+json",
        "Authorization": f"Bearer {access_token}",
        "X-GitHub-Api-Version": "2022-11-28",
    }
    profile_response = client.get("https://api.github.com/user", headers=headers)
    profile_response.raise_for_status()
    profile = profile_response.json()

    provider_user_id = profile.get("id")
    if not isinstance(provider_user_id, int | str):
        raise ValueError("GitHub did not return a user id")

    emails_response = client.get(
        "https://api.github.com/user/emails",
        headers=headers,
    )
    emails_response.raise_for_status()
    selected_email = _github_email(emails_response.json())
    if selected_email is None:
        raise ValueError("GitHub did not return a verified email")
    email, email_verified = selected_email

    return OAuthIdentity(
        provider="github",
        provider_user_id=str(provider_user_id),
        email=email.lower(),
        email_verified=email_verified,
        display_name=(
            profile.get("name")
            if isinstance(profile.get("name"), str)
            else profile.get("login")
            if isinstance(profile.get("login"), str)
            else None
        ),
        avatar_url=(
            profile.get("avatar_url")
            if isinstance(profile.get("avatar_url"), str)
            else None
        ),
    )


def _fetch_oauth_identity(
    *,
    provider: str,
    config: OAuthProviderConfig,
    code: str,
    redirect_uri: str,
) -> OAuthIdentity:
    with httpx.Client(timeout=OAUTH_HTTP_TIMEOUT_SECONDS) as client:
        access_token = _exchange_oauth_code(
            client=client,
            config=config,
            code=code,
            redirect_uri=redirect_uri,
        )
        if provider == "google":
            return _google_identity(client=client, access_token=access_token)
        if provider == "github":
            return _github_identity(client=client, access_token=access_token)
    raise ValueError("Unsupported OAuth provider")


def _user_for_oauth_identity(*, session: Session, identity: OAuthIdentity) -> User:
    account = crud.get_oauth_account(
        session=session,
        provider=identity.provider,
        provider_user_id=identity.provider_user_id,
    )
    if account is not None:
        crud.update_oauth_account_profile(
            session=session,
            account=account,
            email=identity.email,
            email_verified=identity.email_verified,
            display_name=identity.display_name,
            avatar_url=identity.avatar_url,
        )
        user = session.get(User, account.user_id)
        if user is None:
            raise ValueError("OAuth account is not linked to a valid user")
        return user

    user = crud.get_user_by_email(session=session, email=identity.email)
    if user is None:
        user = User(
            email=identity.email,
            full_name=identity.display_name,
            hashed_password=security.get_password_hash(secrets.token_urlsafe(32)),
            has_password=False,
            is_active=True,
            is_superuser=False,
        )
        session.add(user)
        session.flush()

    crud.create_oauth_account(
        session=session,
        user_id=user.id,
        provider=identity.provider,
        provider_user_id=identity.provider_user_id,
        email=identity.email,
        email_verified=identity.email_verified,
        display_name=identity.display_name,
        avatar_url=identity.avatar_url,
    )
    return user


@router.get("/login/{provider}")
def start_oauth_login(provider: str, request: Request) -> RedirectResponse:
    try:
        config = _provider_config(provider)
    except HTTPException as exc:
        if exc.status_code == 503:
            logger.info("OAuth provider %s is not configured", provider)
            return _oauth_error_redirect(_generic_oauth_error_message())
        raise
    state = secrets.token_urlsafe(32)
    redirect_uri = _callback_url(request, provider)
    authorization_params = {
        "client_id": config.client_id,
        "redirect_uri": redirect_uri,
        "response_type": "code",
        "scope": config.scope,
        "state": state,
    }
    authorization_url = f"{config.authorize_url}?{urlencode(authorization_params)}"
    response = RedirectResponse(authorization_url, status_code=307)
    _set_oauth_state_cookie(response, state)
    return response


@router.get("/login/{provider}/callback", name="oauth_callback")
def oauth_callback(
    provider: str,
    request: Request,
    session: SessionDep,
    code: str | None = None,
    state: str | None = None,
    error: str | None = None,
    stored_state: Annotated[
        str | None,
        Cookie(alias=OAUTH_STATE_COOKIE_NAME),
    ] = None,
) -> RedirectResponse:
    if error:
        logger.info("OAuth provider %s returned error: %s", provider, error)
        redirect = _oauth_error_redirect(_provider_error_message(error))
        _clear_oauth_state_cookie(redirect)
        return redirect

    if not code or not state or not stored_state or state != stored_state:
        logger.info("OAuth callback for %s failed state validation", provider)
        redirect = _oauth_error_redirect("Invalid OAuth state")
        _clear_oauth_state_cookie(redirect)
        return redirect

    try:
        config = _provider_config(provider)
        identity = _fetch_oauth_identity(
            provider=provider,
            config=config,
            code=code,
            redirect_uri=_callback_url(request, provider),
        )
        if not identity.email_verified:
            raise ValueError("Provider email is not verified")
        user = _user_for_oauth_identity(session=session, identity=identity)
        if not user.is_active:
            raise ValueError("Inactive user")

        redirect = RedirectResponse(_frontend_redirect("/"), status_code=303)
        _clear_oauth_state_cookie(redirect)
        _issue_session(redirect, session, user.id)
        return redirect
    except (httpx.HTTPError, ValueError) as exc:
        session.rollback()
        logger.info("OAuth callback failed for %s: %s", provider, exc)
        redirect = _oauth_error_redirect(_oauth_failure_message(exc))
        _clear_oauth_state_cookie(redirect)
        return redirect


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
