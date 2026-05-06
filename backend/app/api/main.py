from fastapi import APIRouter

from app.api.routes import (
    admin_embeddings,
    article,
    ingest,
    interest,
    items,
    login,
    private,
    users,
    utils,
)
from app.core.config import settings

api_router = APIRouter()
api_router.include_router(login.router)
api_router.include_router(users.router)
api_router.include_router(utils.router)
api_router.include_router(items.router)
api_router.include_router(article.router)
api_router.include_router(ingest.router)
api_router.include_router(interest.router)
api_router.include_router(admin_embeddings.router)


if settings.ENVIRONMENT == "local":
    api_router.include_router(private.router)
