import contextlib
import os
import tempfile
import uuid

# Must be set before any identity_platform module is imported.
_TMP_DB = os.path.join(tempfile.gettempdir(), f"identity_platform_test_{uuid.uuid4().hex}.db").replace("\\", "/")
os.environ["DATABASE_URL"] = f"sqlite+aiosqlite:///{_TMP_DB}"
os.environ["SECRET_KEY"] = "x" * 32
os.environ["APP_ENV"] = "test"

import pytest_asyncio

from identity_platform.database.session import async_session_factory, dispose_engine, init_models
from identity_platform.repositories.registry import RepositoryRegistry
import identity_platform.models  # noqa: F401 — populate Base.metadata


@pytest_asyncio.fixture(scope="session", autouse=True)
async def _create_schema():
    await init_models()
    yield
    await dispose_engine()
    # Windows refuses to delete a file another handle still has open; these are scratch files in the temp dir.
    for suffix in ("", "-wal", "-shm"):
        with contextlib.suppress(PermissionError, FileNotFoundError):
            os.remove(_TMP_DB + suffix)


@pytest_asyncio.fixture
async def db_session():
    async with async_session_factory() as session:
        yield session
        await session.rollback()


@pytest_asyncio.fixture
async def repos(db_session) -> RepositoryRegistry:
    return RepositoryRegistry(db_session)
