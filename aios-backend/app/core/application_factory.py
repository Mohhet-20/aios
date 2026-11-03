"""Application Factory pattern: `create_app()` builds and fully configures
a FastAPI instance (middleware order, routers, exception handlers, lifespan)
so tests can call it repeatedly with different settings/overrides instead of
importing a single module-level app instance with implicit global state.

Middleware order matters and is documented inline: outermost-registered
middleware runs first on the way in and last on the way out. Security
headers should wrap everything (even error responses); rate limiting should
happen before we do real work; request ID must be established before
logging can tag anything with it.
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware

from app.api.v1.router import api_router
from app.config.settings import get_settings
from app.core.edge_guard import install_edge_guard
from app.core.exception_handlers import register_exception_handlers
from app.core.lifespan import lifespan
from app.middleware.logging_middleware import LoggingMiddleware
from app.middleware.rate_limit_middleware import RateLimitMiddleware
from app.middleware.request_id_middleware import RequestIDMiddleware
from app.middleware.security_headers_middleware import SecurityHeadersMiddleware
from app.routers.v1 import health_router, metrics_router


def create_app() -> FastAPI:
    settings = get_settings()

    app = FastAPI(
        title=settings.app_name,
        version=settings.app_version,
        description=(
            "Enterprise AI Operating System — backend platform. "
            "See /docs for interactive OpenAPI documentation."
        ),
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
        lifespan=lifespan,
    )

    # --- Middleware (registered outer-to-inner; see module docstring) ---
    app.add_middleware(SecurityHeadersMiddleware)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
        expose_headers=["X-Request-ID", "X-Correlation-ID", "X-RateLimit-Remaining"],
    )
    app.add_middleware(GZipMiddleware, minimum_size=1024)
    app.add_middleware(RateLimitMiddleware)
    app.add_middleware(LoggingMiddleware)
    app.add_middleware(RequestIDMiddleware)
    install_edge_guard(app)  # outermost: unauthenticated service-to-service calls never reach the stack

    register_exception_handlers(app)

    # Health/metrics: unversioned, mounted at root for infra tooling.
    app.include_router(health_router.router)
    app.include_router(metrics_router.router)

    # Everything else: versioned under /api/v1 (settings.api_v1_prefix).
    app.include_router(api_router, prefix=settings.api_v1_prefix)

    return app
