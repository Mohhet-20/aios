"""Assigns a request ID (and correlation ID, if the client supplied one via
`X-Correlation-ID`) to every inbound request, stores it in the contextvar-
based context (`app.logging.context`) for the duration of the request, and
echoes it back in the response headers so a client can correlate its request
with server-side logs/traces.
"""

import time

from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response

from app.logging.context import get_request_id, new_request_id, set_context


class RequestIDMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        request_id = new_request_id()
        correlation_id = request.headers.get("x-correlation-id", request_id)
        set_context(request_id, correlation_id)

        start = time.perf_counter()
        response = await call_next(request)
        duration_ms = (time.perf_counter() - start) * 1000

        response.headers["X-Request-ID"] = get_request_id()
        response.headers["X-Correlation-ID"] = correlation_id
        response.headers["X-Response-Time-ms"] = f"{duration_ms:.2f}"
        return response
