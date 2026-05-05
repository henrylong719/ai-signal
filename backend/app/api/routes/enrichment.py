from typing import Any

from fastapi import APIRouter, Depends, HTTPException

from app.api.deps import get_current_active_superuser
from app.services.enrichment import enrichment_enabled
from app.services.enrichment_worker import PollResult, run_enrichment_poll

router = APIRouter(
    prefix="/enrichment",
    tags=["enrichment"],
    # Every route on this router requires a superuser. Triggering enrichment
    # costs real money via the Anthropic API, so we don't expose it publicly.
    dependencies=[Depends(get_current_active_superuser)],
)


@router.post("/run", response_model=PollResult)
async def trigger_enrichment_poll() -> Any:
    """Run one batch of the enrichment worker.

    Processes up to 20 pending articles. If you have a large backlog,
    call this repeatedly — each call drains one batch. The scheduler
    runs the same function on a timer.

    Returns counts of how many rows were fetched, succeeded, failed,
    and how many hit the retry cap on this pass.
    """
    if not enrichment_enabled():
        raise HTTPException(
            status_code=503,
            detail=(
                "Enrichment is disabled: ANTHROPIC_API_KEY is not set. "
                "Configure it in your environment to enable summarization."
            ),
        )
    return await run_enrichment_poll()
