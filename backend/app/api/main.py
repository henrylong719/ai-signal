from fastapi import APIRouter

from app.api.routes import (
    admin_articles,
    admin_embeddings,
    admin_ingest_runs,
    article,
    digest,
    feedback,
    ingest,
    interest,
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
api_router.include_router(article.router)
api_router.include_router(ingest.router)
api_router.include_router(interest.router)
api_router.include_router(feedback.router)
api_router.include_router(admin_articles.router)
api_router.include_router(admin_embeddings.router)
api_router.include_router(admin_ingest_runs.router)
api_router.include_router(digest.router)


if settings.ENVIRONMENT == "local":
    api_router.include_router(private.router)
