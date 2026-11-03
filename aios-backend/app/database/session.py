"""Async SQLAlchemy engine/session factory with connection pooling.

Uses `sqlite+aiosqlite` for local development (zero external dependencies)
and is production-ready for `postgresql+asyncpg://...` via the same
`DATABASE_URL` setting — nothing above this module knows or cares which
database engine is behind it.
"""

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from sqlalchemy import event
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool, StaticPool

from app.config.settings import get_settings
from app.database.base import Base


def create_engine() -> AsyncEngine:
    settings = get_settings()
    connect_args: dict = {}
    engine_kwargs: dict = {"echo": settings.database_echo, "future": True}

    if settings.is_sqlite:
        connect_args["check_same_thread"] = False
        # sqlite3's own busy-timeout: how long a connection will wait for a
        # lock held by another connection before raising "database is
        # locked", instead of failing immediately. Matters a lot for the
        # file-based test database, where many short-lived engines (one per
        # `create_app()` in the test suite) hit the same file concurrently.
        connect_args["timeout"] = 30
        # In-memory SQLite (used for quick scripts) needs a StaticPool so
        # every connection shares the same in-memory database instead of
        # each getting its own throwaway one.
        if ":memory:" in settings.database_url:
            engine_kwargs["poolclass"] = StaticPool
        else:
            # File-based SQLite (dev/test): avoid pooling multiple
            # concurrent connections against the same file, which is what
            # was producing intermittent "database is locked" errors when
            # the full test suite ran many app instances back to back.
            # NullPool opens a fresh connection per checkout and closes it
            # on release, so there's never more than one writer connection
            # alive per unit of work.
            engine_kwargs["poolclass"] = NullPool
    else:
        engine_kwargs["pool_size"] = settings.database_pool_size
        engine_kwargs["pool_pre_ping"] = True

    eng = create_async_engine(settings.database_url, connect_args=connect_args, **engine_kwargs)

    if settings.is_sqlite:
        # WAL mode lets readers and a writer proceed concurrently instead of
        # the default sqlite behavior where a writer blocks all readers.
        # Applied per-connection via a sync event hook (aiosqlite connections
        # are plain sqlite3 connections under the hood).
        @event.listens_for(eng.sync_engine, "connect")
        def _set_sqlite_pragma(dbapi_connection, connection_record):  # noqa: ANN001
            cursor = dbapi_connection.cursor()
            cursor.execute("PRAGMA journal_mode=WAL")
            cursor.execute("PRAGMA busy_timeout=30000")
            cursor.execute("PRAGMA synchronous=NORMAL")
            cursor.close()

    return eng


engine: AsyncEngine = create_engine()
async_session_factory = async_sessionmaker(bind=engine, expire_on_commit=False, class_=AsyncSession)


async def init_models() -> None:
    """Create tables if they don't exist. Used for local/dev/test bootstrap;
    production deployments should run Alembic migrations instead (see
    `alembic/`) so schema changes are reviewed and reversible."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def dispose_engine() -> None:
    await engine.dispose()


@asynccontextmanager
async def session_scope() -> AsyncGenerator[AsyncSession, None]:
    """Context-manager form of a session, for use outside FastAPI's request
    lifecycle — background workers and scripts use this instead of the
    `get_db_session` dependency."""
    async with async_session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI dependency: one session per request, committed on success and
    rolled back on any unhandled exception."""
    async with async_session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()
