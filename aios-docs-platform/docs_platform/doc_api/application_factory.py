"""Application Factory pattern (same as sibling AIOS platforms):
`create_app()` builds a fully-configured FastAPI instance so tests can
build fresh app instances with dependency overrides instead of
importing one module-level global."""
from __future__ import annotations

from fastapi import FastAPI

from docs_platform.doc_api.edge_guard import install_edge_guard

from docs_platform.doc_api.lifespan import lifespan
from docs_platform.doc_api.exception_handlers import register_exception_handlers
from docs_platform.doc_api.v1.health import router as health_router
from docs_platform.doc_api.v1.router import api_router


def create_app() -> FastAPI:
    app = FastAPI(
        title="AIOS Enterprise Documentation, Knowledge Portal & Learning Platform",
        version="1.0.0",
        description="The official source of truth for the AI Operating System: technical/API/SDK/architecture documentation, a knowledge base, a role-based learning platform, an AI documentation assistant, enterprise search, versioning & release notes, collaboration & review workflows, documentation analytics, and RBAC-backed security & governance.",
        docs_url="/docs", redoc_url="/redoc", openapi_url="/openapi.json",
        lifespan=lifespan,
    )

    install_edge_guard(app)
    register_exception_handlers(app)

    app.include_router(health_router)
    app.include_router(api_router, prefix="/api/v1")

    return app
