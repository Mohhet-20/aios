"""Application Factory pattern (same as sibling AIOS platforms):
`create_app()` builds a fully-configured FastAPI instance so tests can
build fresh app instances with dependency overrides instead of
importing one module-level global."""
from __future__ import annotations

from fastapi import FastAPI

from release_platform.release_api.edge_guard import install_edge_guard

from release_platform.release_api.lifespan import lifespan
from release_platform.release_api.exception_handlers import register_exception_handlers
from release_platform.release_api.v1.health import router as health_router
from release_platform.release_api.v1.router import api_router


def create_app() -> FastAPI:
    app = FastAPI(
        title="AIOS Enterprise Release Engineering, Distribution & Deployment Platform",
        version="1.0.0",
        description="Every release of the AI Operating System flows through this platform: release & version management (SemVer, channels, compatibility matrix), artifact management & enterprise distribution (11 artifact types, registries/repositories/offline bundles), deployment orchestration across 9 target types, a 10-strategy rollout engine, a feature flag platform (toggles, targeted overrides, percentage rollouts, kill switches), update infrastructure, license management, environment management, deployment validation & the rollback engine, security & supply chain (signing, SBOM, checksum verification, release approvals), and release observability/analytics.",
        docs_url="/docs", redoc_url="/redoc", openapi_url="/openapi.json",
        lifespan=lifespan,
    )

    install_edge_guard(app)
    register_exception_handlers(app)

    app.include_router(health_router)
    app.include_router(api_router, prefix="/api/v1")

    return app
