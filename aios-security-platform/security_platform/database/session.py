"""Async engine/session management. SQLite needs WAL + a busy timeout +
NullPool to behave under concurrent access in tests and dev — the same
fix every AIOS service needed, applied from the start here.

Two generator helpers with different commit contracts, by design:
`session_scope()` commits on a clean exit and rolls back on exception —
use this anywhere a caller wants normal request-scoped transaction
semantics (this is what the REST API's dependency chain uses).
`get_db_session()` neither commits nor rolls back, for callers (mainly
tests) that want to manage their own transaction boundary explicitly.
Never call `return`/`break` from inside `async for session in
session_scope(): ...` — that closes the generator via `GeneratorExit`
without resuming past the `yield`, so the post-yield commit is silently
skipped. Capture the result in an outer variable and return only after
the loop completes naturally.

Every other AIOS platform's commit-spanning-lock lesson applies again
here: any service method that calls `self.repos.session.commit()`
mid-method (needed when a check-then-act race spans multiple statements
and must be serialized per-key with an in-process lock held across the
commit) will, if exercised through the rollback-isolated test fixture,
durably commit everything written earlier in that same test. See
`tests/conftest.py` for the concrete guard this build uses."""
from __future__ import annotations

from collections.abc import AsyncGenerator

from sqlalchemy import event
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from security_platform.config.settings import get_settings
from security_platform.database.base import Base

_engine: AsyncEngine | None = None
_session_factory: async_sessionmaker[AsyncSession] | None = None


def _configure_sqlite_pragmas(engine: AsyncEngine) -> None:
    @event.listens_for(engine.sync_engine, "connect")
    def _on_connect(dbapi_connection, connection_record):  # noqa: ANN001
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA journal_mode=WAL")
        cursor.execute("PRAGMA busy_timeout=30000")
        cursor.execute("PRAGMA synchronous=NORMAL")
        cursor.close()


def create_engine() -> AsyncEngine:
    settings = get_settings()
    kwargs: dict = {"echo": settings.database_echo}
    if settings.is_sqlite:
        kwargs["poolclass"] = NullPool
    engine = create_async_engine(settings.database_url, **kwargs)
    if settings.is_sqlite:
        _configure_sqlite_pragmas(engine)
    return engine


def get_engine() -> AsyncEngine:
    global _engine
    if _engine is None:
        _engine = create_engine()
    return _engine


def async_session_factory() -> AsyncSession:
    global _session_factory
    if _session_factory is None:
        _session_factory = async_sessionmaker(get_engine(), expire_on_commit=False, class_=AsyncSession)
    return _session_factory()


async def init_models() -> None:
    engine = get_engine()
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def dispose_engine() -> None:
    global _engine, _session_factory
    if _engine is not None:
        await _engine.dispose()
    _engine = None
    _session_factory = None


async def session_scope() -> AsyncGenerator[AsyncSession, None]:
    async with async_session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    """One transaction per request: commit when the handler succeeds, roll back when it raises.

    Without the commit, every write made through the HTTP API was discarded when the session closed.
    """
    async with async_session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
