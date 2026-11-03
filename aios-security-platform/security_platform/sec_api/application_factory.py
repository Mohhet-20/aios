"""Application Factory pattern (same as sibling AIOS platforms):
`create_app()` builds a fully-configured FastAPI instance so tests can
build fresh app instances with dependency overrides instead of
importing one module-level global."""
from __future__ import annotations

from fastapi import FastAPI

from security_platform.sec_api.edge_guard import install_edge_guard

from security_platform.sec_api.lifespan import lifespan
from security_platform.sec_api.exception_handlers import register_exception_handlers
from security_platform.sec_api.v1.health import router as health_router
from security_platform.sec_api.v1.router import api_router


def create_app() -> FastAPI:
    app = FastAPI(
        title="AIOS Enterprise Security, Guardrails & AI Governance Platform",
        version="1.0.0",
        description="AI guardrails, data protection (PII/DLP), the policy engine, secrets management, encryption, risk scoring, threat detection, AI governance, security events, audit, and compliance for every subsystem of the AI Operating System.",
        docs_url="/docs", redoc_url="/redoc", openapi_url="/openapi.json",
        lifespan=lifespan,
    )

    install_edge_guard(app)
    register_exception_handlers(app)

    app.include_router(health_router)
    app.include_router(api_router, prefix="/api/v1")

    return app
