"""Application Factory pattern (same as Phases 3 and 5): `create_app()`
builds a fully-configured FastAPI instance so tests can build fresh app
instances with dependency overrides instead of importing one module-level
global."""
from __future__ import annotations

from fastapi import FastAPI

from agent_platform.agent_api.edge_guard import install_edge_guard

from agent_platform.agent_api.lifespan import lifespan
from agent_platform.agent_api.exception_handlers import register_exception_handlers
from agent_platform.agent_api.v1.health import router as health_router
from agent_platform.agent_api.v1.router import api_router


def create_app() -> FastAPI:
    app = FastAPI(
        title="AIOS Multi-Agent AI Platform",
        version="1.0.0",
        description="Enterprise Multi-Agent AI Platform — the intelligent orchestration layer of the AI Operating System.",
        docs_url="/docs", redoc_url="/redoc", openapi_url="/openapi.json",
        lifespan=lifespan,
    )

    install_edge_guard(app)
    register_exception_handlers(app)

    app.include_router(health_router)
    app.include_router(api_router, prefix="/api/v1")

    return app
