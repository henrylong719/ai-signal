from typing import Any

from fastapi import APIRouter, Depends

from app.api.deps import get_current_active_superuser
from app.crud.ingest import ingest_all

router = APIRouter(
    prefix="/ingest",
    tags=["ingest"],
    dependencies=[Depends(get_current_active_superuser)],
)


@router.post("")
async def trigger_ingest() -> Any:
    return await ingest_all()
