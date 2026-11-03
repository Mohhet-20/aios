"""Application lifecycle events (startup/shutdown), wired via FastAPI's
lifespan context manager rather than the deprecated `@app.on_event`. This is
where cross-cutting infrastructure gets initialized once, in a defined
order, and torn down in reverse.
"""

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.config.settings import get_settings
from app.database.session import dispose_engine, init_models
from app.events.bus import event_bus
from app.events.handlers import register_default_handlers
from app.logging.setup import configure_logging, get_logger
from app.workers.in_process_worker import worker_pool

logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    settings = get_settings()
    configure_logging(settings.log_level, settings.log_json)
    logger.info("startup_begin", app_env=settings.app_env, app_version=settings.app_version)

    if settings.is_sqlite:
        # Dev/test convenience: create tables directly. Production databases
        # are schema-managed via `alembic upgrade head` instead (see
        # scripts/migrate.sh) so this branch never runs against Postgres.
        await init_models()

    register_default_handlers(event_bus)
    await worker_pool.start()

    logger.info("startup_complete")
    yield

    logger.info("shutdown_begin")
    await worker_pool.stop()
    await dispose_engine()
    logger.info("shutdown_complete")
