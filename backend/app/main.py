import logging
import os
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
from app.middleware.response_size import ResponseSizeLogMiddleware
from app.services.scheduler import shutdown_scheduler, start_scheduler


def _configure_logging() -> None:
    """Tame log volume in production.

    Uvicorn configures the root logger before our app code imports run,
    so we don't touch root — we just raise/lower the *named* loggers we
    care about. INFO from ``app.*`` stays visible (digest scheduler,
    ingest summary, etc.) and the chatty third-party libs are muted to
    WARNING so we stop tripping Railway's 500 logs/sec ceiling.
    ``LOG_LEVEL`` env var overrides the app-logger level for ad-hoc
    debugging without a code change.
    """
    app_level = os.getenv("LOG_LEVEL", "INFO").upper()
    logging.getLogger("app").setLevel(app_level)
    for noisy in (
        "httpx",
        "httpcore",
        "apscheduler",
        "urllib3",
    ):
        logging.getLogger(noisy).setLevel(logging.WARNING)


_configure_logging()


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

# Per-request response-size logging. Emits one ``access_size`` log line
# per HTTP request (method, path, status, bytes, duration). Grep these
# lines and aggregate by path to find which endpoints are driving
# network egress — see app/middleware/response_size.py.
app.add_middleware(ResponseSizeLogMiddleware)

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


@app.middleware("http")
async def no_store_api_responses(request: Request, call_next):  # type: ignore[no-untyped-def]
    """Forbid edge caching of API responses.

    Defense in depth against Vercel's edge caching proxied /api/* responses
    keyed only by URL. The frontend already sets ``Cache-Control: no-store``
    on /api/(.*) via vercel.json, but that file is one edit away from being
    wrong. Setting the header upstream means even if vercel.json drops the
    rule, Vercel still sees no-store and won't cache. Uses setdefault so
    individual handlers can still opt into caching by setting their own
    Cache-Control before returning.
    """
    response = await call_next(request)
    if request.url.path.startswith(settings.API_V1_STR):
        response.headers.setdefault("Cache-Control", "no-store")
    return response


app.include_router(api_router, prefix=settings.API_V1_STR)
