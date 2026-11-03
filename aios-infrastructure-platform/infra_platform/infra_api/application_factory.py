"""Application Factory pattern (same as sibling AIOS platforms):
`create_app()` builds a fully-configured FastAPI instance so tests can
build fresh app instances with dependency overrides instead of
importing one module-level global."""
from __future__ import annotations

from fastapi import FastAPI

from infra_platform.infra_api.edge_guard import install_edge_guard

from infra_platform.infra_api.lifespan import lifespan
from infra_platform.infra_api.exception_handlers import register_exception_handlers
from infra_platform.infra_api.v1.health import router as health_router
from infra_platform.infra_api.v1.router import api_router


def create_app() -> FastAPI:
    app = FastAPI(
        title="AIOS Enterprise Production Infrastructure & MLOps Platform",
        version="1.0.0",
        description="Container image registry, Kubernetes control plane, CI/CD, model lifecycle management, experiment tracking, feature store, artifact management, inference platform, deployment strategies, autoscaling, multi-cloud, disaster recovery, observability, and infra security & governance for the AI Operating System.",
        docs_url="/docs", redoc_url="/redoc", openapi_url="/openapi.json",
        lifespan=lifespan,
    )

    install_edge_guard(app)
    register_exception_handlers(app)

    app.include_router(health_router)
    app.include_router(api_router, prefix="/api/v1")

    return app
