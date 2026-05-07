from contextlib import asynccontextmanager

import sentry_sdk
from fastapi import FastAPI
from fastapi.routing import APIRoute
from starlette.middleware.cors import CORSMiddleware

from app.api.main import api_router
from app.core.config import settings
from app.services.scheduler import shutdown_scheduler, start_scheduler


def custom_generate_unique_id(route: APIRoute) -> str:
    return f"{route.tags[0]}-{route.name}"


if settings.SENTRY_DSN and settings.ENVIRONMENT != "local":
    sentry_sdk.init(dsn=str(settings.SENTRY_DSN), enable_tracing=True)


@asynccontextmanager
async def lifespan(app: FastAPI):  # type: ignore[no-untyped-def]
    """Manage long-lived background work alongside the API.

    Currently owns the ingestion scheduler. Anything else that needs
    to start with the app and stop with it (background tasks, cache
    warmers, connection pools) belongs here.
    """
    start_scheduler()
    try:
        yield
    finally:
        shutdown_scheduler()


app = FastAPI(
    title=settings.PROJECT_NAME,
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
    generate_unique_id_function=custom_generate_unique_id,
    lifespan=lifespan,
)

# CORS for credentialed (cookie-bearing) requests has two non-negotiable
# requirements:
#   1. ``allow_credentials=True`` — without it, browsers strip the cookie.
#   2. ``allow_origins`` must be an explicit list, not "*" — browsers refuse
#      credentialed requests against wildcard origins.
# Both are satisfied below. ``settings.all_cors_origins`` includes
# ``FRONTEND_HOST`` (default localhost:5173 in dev); production hosts go in
# the ``BACKEND_CORS_ORIGINS`` env var.
if settings.all_cors_origins:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.all_cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

app.include_router(api_router, prefix=settings.API_V1_STR)
