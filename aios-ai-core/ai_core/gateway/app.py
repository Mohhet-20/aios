"""AI Core / LLM Gateway FastAPI application factory. This is the HTTP
front door to the AI Core for callers that prefer a network hop over an
in-process Python import (a non-Python service, a remote deployment, or a
Python service that wants process isolation from the AI Core). Every route
delegates to the exact same engines an in-process caller would use.
"""
from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI

from ai_core.bootstrap import AICoreContext, aclose_ai_core, build_ai_core
from ai_core.config.settings import AICoreSettings
from ai_core.gateway.edge_guard import install_edge_guard
from ai_core.gateway.exception_handlers import register_exception_handlers
from ai_core.gateway.health import health_router, metrics_router
from ai_core.gateway.routes import router as v1_router
from ai_core.observability.setup import configure_logging


def create_app(settings: AICoreSettings | None = None, *, context: AICoreContext | None = None) -> FastAPI:
    resolved_settings = settings or AICoreSettings()
    configure_logging(resolved_settings)

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        owns_context = context is None
        app.state.ai_core = context or build_ai_core(resolved_settings)
        yield
        if owns_context:
            # Only close provider HTTP clients we built ourselves — a
            # caller-supplied context (tests injecting a scripted provider)
            # owns its own lifecycle and may be reused across app instances.
            await aclose_ai_core(app.state.ai_core)

    app = FastAPI(
        title="AIOS AI Core & LLM Gateway",
        description="Unified abstraction over every AI capability — providers, routing, execution, tools, embeddings.",
        version="1.0.0",
        lifespan=lifespan,
    )
    register_exception_handlers(app)
    install_edge_guard(app)
    app.include_router(health_router)
    app.include_router(metrics_router)
    app.include_router(v1_router, prefix="/v1")
    return app
