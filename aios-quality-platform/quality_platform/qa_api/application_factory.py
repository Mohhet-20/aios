"""Application Factory pattern (same as sibling AIOS platforms):
`create_app()` builds a fully-configured FastAPI instance so tests can
build fresh app instances with dependency overrides instead of
importing one module-level global."""
from __future__ import annotations

from fastapi import FastAPI

from quality_platform.qa_api.edge_guard import install_edge_guard

from quality_platform.qa_api.lifespan import lifespan
from quality_platform.qa_api.exception_handlers import register_exception_handlers
from quality_platform.qa_api.v1.health import router as health_router
from quality_platform.qa_api.v1.router import api_router


def create_app() -> FastAPI:
    app = FastAPI(
        title="AIOS Enterprise Testing, Quality Engineering & Reliability Platform",
        version="1.0.0",
        description="Test automation across the 15-type test pyramid, AI evaluation regression detection, performance/load testing, chaos engineering, security testing, API & workflow validation, reliability engineering (SLOs/error budgets), quality gates & coverage, failure/risk analysis, release certification, and quality observability for the AI Operating System.",
        docs_url="/docs", redoc_url="/redoc", openapi_url="/openapi.json",
        lifespan=lifespan,
    )

    install_edge_guard(app)
    register_exception_handlers(app)

    app.include_router(health_router)
    app.include_router(api_router, prefix="/api/v1")

    return app
