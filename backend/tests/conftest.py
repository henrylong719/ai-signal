# ruff: noqa: E402
import os
from collections.abc import Generator
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text
from sqlalchemy.engine import make_url
from sqlmodel import Session, delete

_BACKEND_DIR = Path(__file__).resolve().parents[1]
_ROOT_DIR = _BACKEND_DIR.parent


def _env_file_value(key: str) -> str | None:
    env_path = _ROOT_DIR / ".env"
    if not env_path.exists():
        return None

    for line in env_path.read_text().splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or "=" not in stripped:
            continue
        name, value = stripped.split("=", maxsplit=1)
        if name.strip() == key:
            return value.strip().strip("\"'")
    return None


def _configure_test_database_name() -> None:
    base_db_name = os.environ.get("POSTGRES_DB") or _env_file_value("POSTGRES_DB")
    test_db_name = os.environ.get("TEST_POSTGRES_DB") or f"{base_db_name or 'app'}_test"
    _assert_test_database_name(test_db_name)
    os.environ["POSTGRES_DB"] = test_db_name


def _assert_test_database_name(db_name: str) -> None:
    if db_name.startswith("test_") or db_name.endswith("_test"):
        return
    raise RuntimeError(
        f'Refusing to run tests against database "{db_name}". '
        'Set TEST_POSTGRES_DB to a name starting with "test_" or ending with "_test".'
    )


_configure_test_database_name()

from app.core.config import settings


def _ensure_test_database_exists() -> None:
    _assert_test_database_name(settings.POSTGRES_DB)
    admin_url = make_url(str(settings.SQLALCHEMY_DATABASE_URI)).set(database="postgres")
    admin_engine = create_engine(admin_url, isolation_level="AUTOCOMMIT")
    try:
        with admin_engine.connect() as connection:
            exists = connection.execute(
                text("SELECT 1 FROM pg_database WHERE datname = :db_name"),
                {"db_name": settings.POSTGRES_DB},
            ).scalar_one_or_none()
            if exists is not None:
                return

            quoted_db_name = connection.dialect.identifier_preparer.quote(
                settings.POSTGRES_DB
            )
            connection.execute(text(f"CREATE DATABASE {quoted_db_name}"))
    finally:
        admin_engine.dispose()


def _run_test_migrations() -> None:
    alembic_cfg = Config(str(_BACKEND_DIR / "alembic.ini"))
    alembic_cfg.set_main_option(
        "script_location", str(_BACKEND_DIR / "app" / "alembic")
    )
    command.upgrade(alembic_cfg, "head")


_ensure_test_database_exists()
_run_test_migrations()

from app.core.db import engine, init_db
from app.main import app
from app.models import Article, Item, OAuthAccount, RefreshSession, User
from tests.utils.user import authentication_token_from_email
from tests.utils.utils import get_superuser_token_headers


def _clear_test_data(session: Session) -> None:
    _assert_test_database_name(settings.POSTGRES_DB)
    statement = delete(Article)
    session.exec(statement)
    statement = delete(Item)
    session.exec(statement)
    statement = delete(RefreshSession)
    session.exec(statement)
    statement = delete(OAuthAccount)
    session.exec(statement)
    statement = delete(User)
    session.exec(statement)
    session.commit()


@pytest.fixture(scope="session", autouse=True)
def db() -> Generator[Session, None, None]:
    with Session(engine) as session:
        _clear_test_data(session)
        init_db(session)
        yield session
        _clear_test_data(session)


@pytest.fixture(scope="module")
def client() -> Generator[TestClient, None, None]:
    with TestClient(app) as c:
        yield c


@pytest.fixture(autouse=True)
def clear_client_cookies(client: TestClient) -> Generator[None, None, None]:
    client.cookies.clear()
    yield
    client.cookies.clear()


@pytest.fixture(scope="module")
def superuser_token_headers(client: TestClient) -> dict[str, str]:
    return get_superuser_token_headers(client)


@pytest.fixture(scope="module")
def normal_user_token_headers(client: TestClient, db: Session) -> dict[str, str]:
    return authentication_token_from_email(
        client=client, email=settings.EMAIL_TEST_USER, db=db
    )
