"""Application Factory pattern (same as sibling AIOS platforms):
`create_app()` builds a fully-configured FastAPI instance so tests can
build fresh app instances with dependency overrides instead of
importing one module-level global."""
from __future__ import annotations

from fastapi import FastAPI

from analytics_platform.an_api.edge_guard import install_edge_guard

from analytics_platform.an_api.lifespan import lifespan
from analytics_platform.an_api.exception_handlers import register_exception_handlers
from analytics_platform.an_api.v1.health import router as health_router
from analytics_platform.an_api.v1.router import api_router


def create_app() -> FastAPI:
    app = FastAPI(
        title="AIOS Enterprise Analytics, Business Intelligence & Executive Reporting Platform",
        version="1.0.0",
        description="Data warehouse, aggregation/analytics engine, KPI engine, reporting platform, forecasting engine, recommendation engine, visualization & dashboard platform, security & governance, and observability for the AI Operating System.",
        docs_url="/docs", redoc_url="/redoc", openapi_url="/openapi.json",
        lifespan=lifespan,
    )

    install_edge_guard(app)
    register_exception_handlers(app)

    app.include_router(health_router)
    app.include_router(api_router, prefix="/api/v1")

    return app
