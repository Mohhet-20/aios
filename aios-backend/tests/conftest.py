"""Shared pytest fixtures.

Uses a temp file-based SQLite database (not `:memory:`) for the test suite.
An in-memory SQLite database only exists for the lifetime of a single
DBAPI connection, and pytest-asyncio's default "auto" mode gives each async
test its own event loop — mixing a pooled `:memory:` connection across
event loops is fragile (the connection can appear empty/"no such table" to
a test running on a different loop than the one that created the schema).
A file-based DB sidesteps this entirely: every new connection, on any
event loop, opens the same file and sees the same schema/data.
"""

import contextlib
import os
import tempfile
import uuid

_TEST_DB_PATH = os.path.join(tempfile.gettempdir(), f"aios_test_{uuid.uuid4().hex}.db").replace("\\", "/")
os.environ.setdefault("DATABASE_URL", f"sqlite+aiosqlite:///{_TEST_DB_PATH}")
os.environ.setdefault("SECRET_KEY", "test-secret-key-not-for-production-use")
os.environ.setdefault("APP_ENV", "test")
os.environ.setdefault("RATE_LIMIT_REQUESTS", "10000")  # tests shouldn't trip the rate limiter

from collections.abc import AsyncGenerator  # noqa: E402

import httpx  # noqa: E402
import pytest_asyncio  # noqa: E402

from app.config.settings import get_settings  # noqa: E402
from app.core.application_factory import create_app  # noqa: E402
from app.database.base import Base  # noqa: E402
from app.database.session import async_session_factory, engine  # noqa: E402

get_settings.cache_clear()


@pytest_asyncio.fixture(scope="session", autouse=True)
async def _create_schema():
    import app.models  # noqa: F401 — populate Base.metadata

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    await engine.dispose()
    # Windows refuses to delete a file another handle still has open; it is a scratch file in the temp dir.
    with contextlib.suppress(PermissionError, FileNotFoundError):
        os.remove(_TEST_DB_PATH)


@pytest_asyncio.fixture
async def db_session():
    async with async_session_factory() as session:
        yield session
        await session.rollback()


@pytest_asyncio.fixture
async def client() -> AsyncGenerator[httpx.AsyncClient, None]:
    app = create_app()
    transport = httpx.ASGITransport(app=app)
    async with app.router.lifespan_context(app):
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as ac:
            yield ac


@pytest_asyncio.fixture
async def registered_user(client: httpx.AsyncClient):
    payload = {
        "email": f"tester-{uuid.uuid4().hex[:8]}@aios.dev",
        "password": "supersecret123",
        "full_name": "Test User",
    }
    response = await client.post("/api/v1/auth/register", json=payload)
    assert response.status_code == 201
    return payload


@pytest_asyncio.fixture
async def auth_headers(client: httpx.AsyncClient, registered_user: dict):
    response = await client.post(
        "/api/v1/auth/login",
        json={"email": registered_user["email"], "password": registered_user["password"]},
    )
    assert response.status_code == 200
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}
