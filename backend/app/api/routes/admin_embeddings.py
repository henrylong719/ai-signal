"""Admin endpoint for the article embedding backfill.

Superuser-only. The endpoint is intentionally bounded — it processes
at most a few batches per call and returns counts so the caller knows
whether more work remains. For seeding a fresh DB with thousands of
articles, use the CLI script in ``app.scripts.backfill_embeddings``
which loops automatically.

POST /admin/embed-articles
  Optional query params:
    batch_size  (default 32, max 64)  — articles per batch
    max_batches (default 4,  max 10)  — batches per call
  Returns: { processed, remaining, batches }
"""

import logging
from typing import Any

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel

from app.api.deps import SessionDep, get_current_active_superuser
from app.services.embeddings import backfill_article_embeddings

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/admin",
    tags=["admin"],
    dependencies=[Depends(get_current_active_superuser)],
)


class BackfillResponse(BaseModel):
    """Wire shape of the backfill report.

    Mirrors ``services.embeddings.BackfillReport`` but as a Pydantic
    BaseModel so FastAPI serializes it cleanly without a custom encoder.
    """

    processed: int
    remaining: int
    batches: int


@router.post("/embed-articles", response_model=BackfillResponse)
def embed_pending_articles(
    session: SessionDep,
    batch_size: int = Query(default=32, ge=1, le=64),
    max_batches: int = Query(default=4, ge=1, le=10),
) -> Any:
    """Encode the next chunk of articles missing embeddings.

    Bounded per call so the request returns in seconds even if there
    are thousands of pending articles. Operators handle "embed
    everything" by calling repeatedly or by running the CLI script.

    The endpoint is synchronous: it blocks until the work is done and
    then returns the counts. Failures propagate as HTTP 500 so the
    operator sees what broke (a missing model file, an OOM, etc.) —
    not a silent partial success.
    """
    report = backfill_article_embeddings(
        session=session,
        batch_size=batch_size,
        max_batches=max_batches,
    )
    if report.processed > 0:
        logger.info(
            "Embedding backfill: processed=%d remaining=%d batches=%d",
            report.processed,
            report.remaining,
            report.batches,
        )
    return BackfillResponse(
        processed=report.processed,
        remaining=report.remaining,
        batches=report.batches,
    )
