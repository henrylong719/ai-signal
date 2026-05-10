"""Protected internal endpoint that triggers the article cleanup pipeline.

Designed for external cron services (Render Cron, Railway Cron, GitHub
Actions, etc.). Not for end users and not for the SPA — there's no
session here, only a shared secret in the ``Authorization`` header.

Safety contract:

  - If ``ARTICLE_CLEANUP_CRON_SECRET`` is unset the endpoint always
    refuses (503). This prevents a misconfigured deploy from exposing
    an unauthenticated destructive endpoint.
  - The endpoint runs under the global ``ARTICLE_CLEANUP_DRY_RUN``
    default. A caller can pass ``?dry_run=true`` to force dry-run on
    a non-dry-run deploy, but cannot pass ``?dry_run=false`` to
    downgrade safety when ``ARTICLE_CLEANUP_DRY_RUN=True`` is set —
    safety only ever escalates here.
"""

from __future__ import annotations

import logging
from typing import Annotated, Any

from fastapi import APIRouter, Header, HTTPException, Query, status
from sqlmodel import SQLModel

from app.api.deps import SessionDep
from app.core.config import settings
from app.services.article_cleanup import run_article_cleanup

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/internal", tags=["internal"])


class ArticleCleanupResponse(SQLModel):
    archived_count: int
    deleted_count: int
    dry_run: bool
    archive_cutoff: str | None
    delete_cutoff: str | None
    keep_clicked_since: str | None
    errors: list[str]


def _require_bearer_secret(authorization: str | None) -> None:
    """Validate the ``Authorization: Bearer <secret>`` header.

    Raises 503 when no secret is configured (so an operator can't ship
    the endpoint open by accident) and 401 on a bad/missing header.
    Distinguishing 503 from 401 makes the cause of a failed external
    cron call obvious from the response code.
    """
    expected = settings.ARTICLE_CLEANUP_CRON_SECRET
    if not expected:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Article cleanup endpoint is not configured",
        )
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing or invalid Authorization header",
        )
    provided = authorization.split(" ", 1)[1].strip()
    # Constant-time compare so a remote attacker can't time-probe the
    # secret one byte at a time.
    import hmac

    if not hmac.compare_digest(provided, expected):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid cleanup secret",
        )


@router.post("/article-cleanup", response_model=ArticleCleanupResponse)
def trigger_article_cleanup(
    session: SessionDep,
    authorization: Annotated[str | None, Header()] = None,
    dry_run: Annotated[
        bool | None,
        Query(
            description=(
                "Override request-level dry_run. Can force dry-run on a "
                "live deploy, but cannot downgrade an environment-level "
                "ARTICLE_CLEANUP_DRY_RUN=True default."
            )
        ),
    ] = None,
) -> Any:
    """Run the cleanup pipeline once and return a JSON summary.

    Intended for external cron triggers. The handler delegates to the
    same ``run_article_cleanup`` used by the manual script and the
    in-process scheduled job, so all three paths produce identical
    behavior.
    """
    _require_bearer_secret(authorization)

    if not settings.ARTICLE_CLEANUP_ENABLED:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Article cleanup is disabled (ARTICLE_CLEANUP_ENABLED=False)",
        )

    # Resolve effective dry-run with the "safety only escalates" rule:
    # if global is dry-run, the request is dry-run no matter what the
    # caller passes. If global is non-dry-run, the caller can still
    # override to dry-run for a one-off check.
    if settings.ARTICLE_CLEANUP_DRY_RUN:
        effective_dry_run = True
    else:
        effective_dry_run = True if dry_run is True else False

    result = run_article_cleanup(session=session, dry_run=effective_dry_run)

    return ArticleCleanupResponse(
        archived_count=result.archived_count,
        deleted_count=result.deleted_count,
        dry_run=result.dry_run,
        archive_cutoff=(
            result.archive_cutoff.isoformat() if result.archive_cutoff else None
        ),
        delete_cutoff=(
            result.delete_cutoff.isoformat() if result.delete_cutoff else None
        ),
        keep_clicked_since=(
            result.keep_clicked_since.isoformat() if result.keep_clicked_since else None
        ),
        errors=result.errors,
    )
