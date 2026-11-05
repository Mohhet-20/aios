"""Async SQLAlchemy engine/session factory — same WAL/busy-timeout/NullPool
fix for file-based SQLite discovered while building the AIOS backend
(the core backend), applied proactively here since the failure mode (many
short-lived app instances / test clients hitting one file concurrently)
is identical for this platform's test suite."""
from __future__ import annotations

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from sqlalchemy import event
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool, StaticPool

from prompt_platform.config.settings import get_settings
from prompt_platform.database.base import Base


def create_engine() -> AsyncEngine:
    settings = get_settings()
    connect_args: dict = {}
    engine_kwargs: dict = {"echo": settings.database_echo, "future": True}

    if settings.is_sqlite:
        connect_args["check_same_thread"] = False
        connect_args["timeout"] = 30
        if ":memory:" in settings.database_url:
            engine_kwargs["poolclass"] = StaticPool
        else:
            engine_kwargs["poolclass"] = NullPool
    else:
        engine_kwargs["pool_size"] = settings.database_pool_size
        engine_kwargs["pool_pre_ping"] = True

    eng = create_async_engine(settings.database_url, connect_args=connect_args, **engine_kwargs)

    if settings.is_sqlite:
        @event.listens_for(eng.sync_engine, "connect")
        def _set_sqlite_pragma(dbapi_connection, connection_record):
            cursor = dbapi_connection.cursor()
            cursor.execute("PRAGMA journal_mode=WAL")
            cursor.execute("PRAGMA busy_timeout=30000")
            cursor.execute("PRAGMA synchronous=NORMAL")
            cursor.close()

    return eng


engine: AsyncEngine = create_engine()
async_session_factory = async_sessionmaker(bind=engine, expire_on_commit=False, class_=AsyncSession)


async def init_models() -> None:
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def dispose_engine() -> None:
    await engine.dispose()


@asynccontextmanager
async def session_scope() -> AsyncGenerator[AsyncSession, None]:
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
    async with async_session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()
