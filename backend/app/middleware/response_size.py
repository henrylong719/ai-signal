"""ASGI middleware that logs response size per request.

Used to diagnose network egress: tail or query the application logs and
group ``access_size`` lines by ``path`` to find which endpoints are
shipping the most bytes. Wrapping the ASGI ``send`` callable means the
body byte count is taken from the actual frames sent on the wire, so
streaming responses are measured accurately.
"""

from __future__ import annotations

import logging
import time
from collections.abc import Callable, MutableMapping
from typing import Any

logger = logging.getLogger("app.access_size")


class ResponseSizeLogMiddleware:
    def __init__(self, app: Callable[..., Any]) -> None:
        self.app = app

    async def __call__(
        self,
        scope: MutableMapping[str, Any],
        receive: Callable[..., Any],
        send: Callable[..., Any],
    ) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        start = time.perf_counter()
        status = 0
        bytes_sent = 0

        async def send_wrapper(message: MutableMapping[str, Any]) -> None:
            nonlocal status, bytes_sent
            if message["type"] == "http.response.start":
                status = int(message.get("status", 0))
            elif message["type"] == "http.response.body":
                body = message.get("body", b"")
                if body:
                    bytes_sent += len(body)
            await send(message)

        try:
            await self.app(scope, receive, send_wrapper)
        finally:
            duration_ms = (time.perf_counter() - start) * 1000
            logger.debug(
                "access_size method=%s path=%s status=%d bytes=%d duration_ms=%.1f",
                scope.get("method", "?"),
                scope.get("path", "?"),
                status,
                bytes_sent,
                duration_ms,
            )
