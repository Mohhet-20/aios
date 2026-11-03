"""Application Factory pattern (same as sibling AIOS platforms):
`create_app()` builds a fully-configured FastAPI instance so tests can
build fresh app instances with dependency overrides instead of importing
one module-level global."""
from __future__ import annotations

from fastapi import FastAPI

from collaboration_platform.collab_api.edge_guard import install_edge_guard

from collaboration_platform.collab_api.lifespan import lifespan
from collaboration_platform.collab_api.exception_handlers import register_exception_handlers
from collaboration_platform.collab_api.v1.health import router as health_router
from collaboration_platform.collab_api.v1.router import api_router


def create_app() -> FastAPI:
    app = FastAPI(
        title="AIOS Enterprise Collaboration & Workspace Platform",
        version="1.0.0",
        description="The collaborative layer for every AIOS subsystem — shared workspaces, real-time collaboration, comments, mentions, activity feeds, notifications, reviews, approvals, version history, shared libraries, search, and team productivity.",
        docs_url="/docs", redoc_url="/redoc", openapi_url="/openapi.json",
        lifespan=lifespan,
    )

    install_edge_guard(app)
    register_exception_handlers(app)

    app.include_router(health_router)
    app.include_router(api_router, prefix="/api/v1")

    return app
