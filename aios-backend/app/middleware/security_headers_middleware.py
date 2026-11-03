"""Baseline security response headers. CSRF is not applicable here since
AIOS is a token-based (JWT/API-key) JSON API with no cookie-based session
auth — CSRF matters for cookie-authenticated browser form submissions,
which this API deliberately does not use (see `SECURITY.md`/self-review for
the full reasoning). `X-Content-Type-Options`/`X-Frame-Options`/HSTS still
apply regardless of auth scheme.
"""

from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response

from app.config.settings import get_settings


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        if get_settings().is_production:
            response.headers["Strict-Transport-Security"] = "max-age=63072000; includeSubDomains"
        return response
