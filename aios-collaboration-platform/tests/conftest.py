import contextlib
import os
import tempfile
import uuid

# Must be set before any collaboration_platform module is imported.
_TMP_DB = os.path.join(tempfile.gettempdir(), f"collaboration_platform_test_{uuid.uuid4().hex}.db").replace("\\", "/")
os.environ["DATABASE_URL"] = f"sqlite+aiosqlite:///{_TMP_DB}"
os.environ["SECRET_KEY"] = "x" * 32
os.environ["APP_ENV"] = "test"

import pytest_asyncio

from collaboration_platform.database.session import async_session_factory, dispose_engine, init_models
from collaboration_platform.repositories.registry import RepositoryRegistry
import collaboration_platform.models  # noqa: F401 — populate Base.metadata


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
    """Rollback-isolated by default — BUT a handful of services
    (`EditSessionService.start_session`, `ReviewService.approve`/
    `reject`) deliberately call `self.repos.session.commit()`
    mid-method, because their correctness under real concurrency
    requires an in-process lock held across the commit, not just the
    read/write (see those services' docstrings). Calling one of those
    methods through this fixture durably commits everything written
    earlier in the same test, bypassing this teardown's rollback. If a
    test exercises one of those methods, don't reuse a generic id
    ("user-2", etc.) that another test's exact-count assertion might
    depend on staying isolated — see `tests/observability/
    test_observability.py`'s `_OBS_USER` for the pattern."""
    async with async_session_factory() as session:
        yield session
        await session.rollback()


@pytest_asyncio.fixture
async def repos(db_session) -> RepositoryRegistry:
    return RepositoryRegistry(db_session)
