from typing import Any

from fastapi import APIRouter, Depends

from app.api.deps import get_current_active_superuser
from app.services.ingest_runner import run_tracked_ingest

router = APIRouter(
    prefix="/ingest",
    tags=["ingest"],
    dependencies=[Depends(get_current_active_superuser)],
)


@router.post("")
async def trigger_ingest() -> Any:
    """Manually trigger an ingestion run.

    Goes through the tracked wrapper, so manual runs show up in the
    admin page alongside scheduled ones. The response includes a
    ``run_id`` so the caller can find the row.
    """
    return await run_tracked_ingest()
