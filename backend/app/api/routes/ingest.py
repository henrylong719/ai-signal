from typing import Any

from fastapi import APIRouter

from app.crud.ingest import ingest_all

router = APIRouter(prefix="/ingest", tags=["ingest"])


@router.post("")
async def trigger_ingest() -> Any:
    return await ingest_all()
