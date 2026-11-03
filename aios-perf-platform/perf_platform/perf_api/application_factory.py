"""Application Factory pattern (same as sibling AIOS platforms):
`create_app()` builds a fully-configured FastAPI instance so tests can
build fresh app instances with dependency overrides instead of
importing one module-level global."""
from __future__ import annotations

from fastapi import FastAPI

from perf_platform.perf_api.edge_guard import install_edge_guard

from perf_platform.perf_api.lifespan import lifespan
from perf_platform.perf_api.exception_handlers import register_exception_handlers
from perf_platform.perf_api.v1.health import router as health_router
from perf_platform.perf_api.v1.router import api_router


def create_app() -> FastAPI:
    app = FastAPI(
        title="AIOS Enterprise Performance Optimization, Cost Intelligence & Scalability Platform",
        version="1.0.0",
        description=(
            "Multi-level caching (memory L1 + DB-backed L2 across 11 declared layers), "
            "LLM cost-intelligence model routing (task-complexity-driven tier selection with "
            "org/workspace policy overrides), real-time cost tracking & budget enforcement, "
            "an auto-optimization recommendation engine that mines cache/latency/routing/budget "
            "signals, and observability (latency percentiles, throughput, benchmark runs) plus "
            "GPU pool inventory for scalability planning."
        ),
        docs_url="/docs", redoc_url="/redoc", openapi_url="/openapi.json",
        lifespan=lifespan,
    )

    install_edge_guard(app)
    register_exception_handlers(app)

    app.include_router(health_router)
    app.include_router(api_router, prefix="/api/v1")

    return app
