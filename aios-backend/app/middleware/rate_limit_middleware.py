"""In-process sliding-window rate limiter, keyed by client IP (falls back to
API key / user ID when authenticated — see the `X-API-Key`/`Authorization`
header check below, which lets an authenticated caller get its own bucket
rather than sharing one with every anonymous request from the same NAT).

This is intentionally a single-process implementation (a plain dict +
deque), which is the correct scope for one Uvicorn worker in dev/test. In a
multi-instance production deployment this needs a shared store (Redis
`INCR`+`EXPIRE`, or a library like `slowapi`/`limits` backed by Redis) so
limits are enforced cluster-wide rather than per-instance — noted explicitly
here rather than silently shipping a limiter that looks like it works but
doesn't, at scale.
"""

import time
from collections import defaultdict, deque

from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

from app.config.settings import get_settings

_EXEMPT_PATHS = {"/health", "/health/live", "/health/ready", "/metrics", "/docs", "/openapi.json", "/redoc"}


class RateLimitMiddleware(BaseHTTPMiddleware):
    def __init__(self, app):
        super().__init__(app)
        self._hits: dict[str, deque[float]] = defaultdict(deque)

    def _client_key(self, request: Request) -> str:
        api_key = request.headers.get("x-api-key")
        if api_key:
            return f"apikey:{api_key[:16]}"
        auth = request.headers.get("authorization")
        if auth:
            return f"auth:{hash(auth) % 10_000_000}"
        return f"ip:{request.client.host if request.client else 'unknown'}"

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        if request.url.path in _EXEMPT_PATHS:
            return await call_next(request)

        settings = get_settings()
        key = self._client_key(request)
        now = time.monotonic()
        window = self._hits[key]

        while window and now - window[0] > settings.rate_limit_window_seconds:
            window.popleft()

        if len(window) >= settings.rate_limit_requests:
            retry_after = settings.rate_limit_window_seconds - (now - window[0])
            return JSONResponse(
                status_code=429,
                content={
                    "error": {
                        "code": "rate_limit_exceeded",
                        "message": "Too many requests. Please slow down.",
                        "details": {"retry_after_seconds": round(max(retry_after, 0), 1)},
                    }
                },
                headers={"Retry-After": str(int(max(retry_after, 1)))},
            )

        window.append(now)
        response = await call_next(request)
        response.headers["X-RateLimit-Limit"] = str(settings.rate_limit_requests)
        response.headers["X-RateLimit-Remaining"] = str(max(settings.rate_limit_requests - len(window), 0))
        return response
