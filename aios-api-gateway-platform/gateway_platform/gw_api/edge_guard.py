"""Service edge guard: who may call this service, and from which browser origins.

Every AIOS domain service sits behind the console's server-side edge (the BFF), which authenticates
users and forwards their verified identity. This module makes that boundary enforceable instead of
assumed:

* ``AIOS_INTERNAL_TOKEN`` set: every route except ``/health*`` requires ``X-Internal-Token`` with
  that value (constant-time comparison). Requests without it get 401 before reaching any router.
  Unset, the service is open, which is the local-development and test default.
* ``APP_ENV=production`` without a token of at least 32 characters: the service refuses to start.
* ``AIOS_CORS_ORIGINS`` (comma separated): browser origins allowed to call the service directly.
  Empty by default, because browsers reach services only through the edge, server to server.

Each service carries its own copy so it stays independently deployable; keep the copies identical.
"""
from __future__ import annotations

import hmac
import json
import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

OPEN_PATH_PREFIXES = ("/health",)
MIN_PRODUCTION_TOKEN_LENGTH = 32


class InternalTokenMiddleware:
    """Pure ASGI middleware: rejects non-health HTTP requests without the right X-Internal-Token."""

    def __init__(self, app, token: bytes) -> None:
        self.app = app
        self.token = token

    async def __call__(self, scope, receive, send) -> None:
        if scope["type"] != "http" or scope["path"].startswith(OPEN_PATH_PREFIXES):
            await self.app(scope, receive, send)
            return
        supplied = next((v for k, v in scope["headers"] if k == b"x-internal-token"), b"")
        if hmac.compare_digest(supplied, self.token):
            await self.app(scope, receive, send)
            return
        detail = "missing or invalid internal service token"
        body = json.dumps({"error": "Unauthorized", "detail": detail}).encode()
        await send({
            "type": "http.response.start",
            "status": 401,
            "headers": [(b"content-type", b"application/json"), (b"content-length", str(len(body)).encode())],
        })
        await send({"type": "http.response.body", "body": body})


def install_edge_guard(app: FastAPI) -> None:
    token = os.environ.get("AIOS_INTERNAL_TOKEN", "").strip()
    production = os.environ.get("APP_ENV", "development").lower() == "production"
    if production and len(token) < MIN_PRODUCTION_TOKEN_LENGTH:
        raise RuntimeError(
            "AIOS_INTERNAL_TOKEN must be set to at least "
            f"{MIN_PRODUCTION_TOKEN_LENGTH} characters in production"
        )
    origins = [o.strip() for o in os.environ.get("AIOS_CORS_ORIGINS", "").split(",") if o.strip()]
    if origins:
        app.add_middleware(CORSMiddleware, allow_origins=origins, allow_credentials=True,
                           allow_methods=["*"], allow_headers=["*"])
    if token:
        app.add_middleware(InternalTokenMiddleware, token=token.encode())
