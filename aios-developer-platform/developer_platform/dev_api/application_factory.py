"""Application Factory pattern (same as sibling AIOS platforms):
`create_app()` builds a fully-configured FastAPI instance so tests can
build fresh app instances with dependency overrides instead of
importing one module-level global."""
from __future__ import annotations

from fastapi import FastAPI

from developer_platform.dev_api.edge_guard import install_edge_guard

from developer_platform.dev_api.lifespan import lifespan
from developer_platform.dev_api.exception_handlers import register_exception_handlers
from developer_platform.dev_api.v1.health import router as health_router
from developer_platform.dev_api.v1.router import api_router


def create_app() -> FastAPI:
    app = FastAPI(
        title="AIOS Enterprise Developer Platform & SDK Ecosystem",
        version="1.0.0",
        description="API platform, Python SDK, CLI, plugin SDK, extension framework, webhooks, MCP integration, code generation, developer portal & sandboxes, package registry, developer analytics, and developer-facing security for the AI Operating System.",
        docs_url="/docs", redoc_url="/redoc", openapi_url="/openapi.json",
        lifespan=lifespan,
    )

    install_edge_guard(app)
    register_exception_handlers(app)

    app.include_router(health_router)
    app.include_router(api_router, prefix="/api/v1")

    return app
