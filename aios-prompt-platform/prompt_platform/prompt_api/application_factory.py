"""Application Factory pattern (same as the AIOS backend from Phase 3):
`create_app()` builds a fully-configured FastAPI instance so tests can
build fresh app instances with dependency overrides instead of importing
one module-level global."""
from __future__ import annotations

from fastapi import FastAPI

from prompt_platform.prompt_api.edge_guard import install_edge_guard

from prompt_platform.prompt_api.lifespan import lifespan
from prompt_platform.prompt_api.exception_handlers import register_exception_handlers
from prompt_platform.prompt_api.v1.health import router as health_router
from prompt_platform.prompt_api.v1.router import api_router


def create_app() -> FastAPI:
    app = FastAPI(
        title="AIOS Prompt Engineering Platform",
        version="1.0.0",
        description="Enterprise Prompt Engineering Platform — design, test, evaluate, optimize, experiment, deploy, and govern prompts at production scale.",
        docs_url="/docs", redoc_url="/redoc", openapi_url="/openapi.json",
        lifespan=lifespan,
    )

    install_edge_guard(app)
    register_exception_handlers(app)

    app.include_router(health_router)
    app.include_router(api_router, prefix="/api/v1")

    return app
