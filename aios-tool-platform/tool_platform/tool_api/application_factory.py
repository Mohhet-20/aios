"""Application Factory pattern (same as sibling AIOS platforms):
`create_app()` builds a fully-configured FastAPI instance so tests can
build fresh app instances with dependency overrides instead of importing
one module-level global."""
from __future__ import annotations

from fastapi import FastAPI

from tool_platform.tool_api.edge_guard import install_edge_guard

from tool_platform.tool_api.lifespan import lifespan
from tool_platform.tool_api.exception_handlers import register_exception_handlers
from tool_platform.tool_api.v1.health import router as health_router
from tool_platform.tool_api.v1.router import api_router


def create_app() -> FastAPI:
    app = FastAPI(
        title="AIOS Enterprise Tool Execution & Integration Platform",
        version="1.0.0",
        description="Enterprise Tool Execution & Integration Platform — the secure universal execution layer of the AI Operating System.",
        docs_url="/docs", redoc_url="/redoc", openapi_url="/openapi.json",
        lifespan=lifespan,
    )

    install_edge_guard(app)
    register_exception_handlers(app)

    app.include_router(health_router)
    app.include_router(api_router, prefix="/api/v1")

    return app
