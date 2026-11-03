"""Application lifecycle events (startup/shutdown), wired via FastAPI's
`lifespan` context manager. Added during the Phase 24 production-hardening
pass: previously this platform's FastAPI app had no lifespan hook at all,
so schema creation only ever happened inside tests (via the `repos`
fixture/`init_models` call) and the database engine connection pool was
never disposed on shutdown — both real gaps for a standalone deployment.
"""
from __future__ import annotations

import logging
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from security_platform.config.settings import get_settings
from security_platform.database.session import dispose_engine, init_models

logger = logging.getLogger("security_platform")


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    settings = get_settings()
    if settings.is_sqlite:
        # Dev/test convenience: create tables directly from the ORM models.
        # Production Postgres deployments are expected to provision schema
        # out-of-band for now — no migration framework (e.g. Alembic) is
        # wired up in this platform yet; see the repo README's deployment
        # notes for the current disclosed scope boundary.
        await init_models()
    logger.info("security_platform startup complete")
    yield
    await dispose_engine()
    logger.info("security_platform shutdown complete")
