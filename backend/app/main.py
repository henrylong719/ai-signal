from contextlib import asynccontextmanager

import sentry_sdk
from fastapi import FastAPI, Request
from fastapi.routing import APIRoute
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
from starlette.middleware.cors import CORSMiddleware
from starlette.responses import Response

from app.api.main import api_router
from app.core.config import settings
from app.core.rate_limit import limiter
from app.services.scheduler import shutdown_scheduler, start_scheduler


def _rate_limit_handler(request: Request, exc: Exception) -> Response:
    """Adapter: Starlette's exception-handler signature requires the
    second parameter to be ``Exception``, but slowapi's handler narrows
    it to ``RateLimitExceeded``. Wrapping keeps both type checkers happy
    without changing behavior — non-RateLimitExceeded would never reach
    this handler since it's registered for that exception class.
    """
    assert isinstance(exc, RateLimitExceeded)
    return _rate_limit_exceeded_handler(request, exc)


def custom_generate_unique_id(route: APIRoute) -> str:
    return f"{route.tags[0]}-{route.name}"


if settings.SENTRY_DSN and settings.ENVIRONMENT != "local":
    sentry_sdk.init(dsn=str(settings.SENTRY_DSN), enable_tracing=True)


@asynccontextmanager
async def lifespan(_app: FastAPI):  # type: ignore[no-untyped-def]
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

# Rate limiting wiring. The limiter itself is configured in
# app/core/rate_limit.py; here we expose it on app.state (slowapi reads
# it from there inside the @limiter.limit decorator), register the 429
# handler so callers get a structured response with a Retry-After header,
# and add the middleware that actually inspects each request.
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_handler)
app.add_middleware(SlowAPIMiddleware)

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
