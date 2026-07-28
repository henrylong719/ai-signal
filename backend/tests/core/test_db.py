from sqlalchemy.pool import NullPool

from app.core.db import async_engine, engine


def test_sync_engine_checks_connections_before_checkout() -> None:
    assert engine.pool._pre_ping is True  # noqa: SLF001


def test_ingest_async_engine_does_not_reuse_idle_connections() -> None:
    assert isinstance(async_engine.pool, NullPool)
