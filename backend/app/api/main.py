from fastapi import APIRouter

from app.api.routes import (
    admin_articles,
    admin_email_preview,
    admin_embeddings,
    admin_ingest_runs,
    article,
    digest,
    feedback,
    guest_analytics,
    ingest,
    interest,
    internal_cleanup,
    login,
    private,
    subscription,
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
api_router.include_router(admin_email_preview.router)
api_router.include_router(admin_ingest_runs.router)
api_router.include_router(digest.router)
api_router.include_router(subscription.router)
api_router.include_router(internal_cleanup.router)
api_router.include_router(guest_analytics.router)


if settings.ENVIRONMENT == "local":
    api_router.include_router(private.router)
