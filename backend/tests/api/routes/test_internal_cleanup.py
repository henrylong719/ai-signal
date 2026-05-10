"""Tests for the protected internal article-cleanup endpoint."""

from __future__ import annotations

from collections.abc import Generator

import pytest
from fastapi.testclient import TestClient

from app.core.config import settings


@pytest.fixture
def cleanup_secret() -> Generator[str, None, None]:
    """Temporarily configure a cron secret for the test.

    The endpoint refuses (503) when ``ARTICLE_CLEANUP_CRON_SECRET`` is
    unset, so the auth tests need a known good secret to compare
    against. We restore the original value on teardown so the rest of
    the suite sees the unmodified setting.
    """
    secret = "test-cleanup-secret"
    original = settings.ARTICLE_CLEANUP_CRON_SECRET
    settings.ARTICLE_CLEANUP_CRON_SECRET = secret
    try:
        yield secret
    finally:
        settings.ARTICLE_CLEANUP_CRON_SECRET = original


def test_cleanup_endpoint_returns_503_when_secret_unset(client: TestClient) -> None:
    # Ensure secret is unset for this test.
    original = settings.ARTICLE_CLEANUP_CRON_SECRET
    settings.ARTICLE_CLEANUP_CRON_SECRET = None
    try:
        response = client.post(
            f"{settings.API_V1_STR}/internal/article-cleanup",
            headers={"Authorization": "Bearer anything"},
        )
        assert response.status_code == 503
    finally:
        settings.ARTICLE_CLEANUP_CRON_SECRET = original


def test_cleanup_endpoint_rejects_missing_authorization(
    client: TestClient, cleanup_secret: str
) -> None:
    response = client.post(f"{settings.API_V1_STR}/internal/article-cleanup")
    assert response.status_code == 401


def test_cleanup_endpoint_rejects_wrong_secret(
    client: TestClient, cleanup_secret: str
) -> None:
    response = client.post(
        f"{settings.API_V1_STR}/internal/article-cleanup",
        headers={"Authorization": "Bearer wrong-secret"},
    )
    assert response.status_code == 401


def test_cleanup_endpoint_accepts_correct_secret_and_returns_summary(
    client: TestClient, cleanup_secret: str
) -> None:
    response = client.post(
        f"{settings.API_V1_STR}/internal/article-cleanup",
        headers={"Authorization": f"Bearer {cleanup_secret}"},
    )
    assert response.status_code == 200
    body = response.json()
    assert {"archived_count", "deleted_count", "dry_run", "errors"} <= body.keys()
    # The default settings have ARTICLE_CLEANUP_DRY_RUN=True so the
    # endpoint must run in dry-run mode regardless of query param.
    assert body["dry_run"] is True


def test_cleanup_endpoint_cannot_downgrade_dry_run_safety(
    client: TestClient, cleanup_secret: str
) -> None:
    """``?dry_run=false`` is ignored when global dry-run is True."""
    response = client.post(
        f"{settings.API_V1_STR}/internal/article-cleanup?dry_run=false",
        headers={"Authorization": f"Bearer {cleanup_secret}"},
    )
    assert response.status_code == 200
    assert response.json()["dry_run"] is True
