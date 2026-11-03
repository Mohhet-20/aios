import contextlib
import os
import tempfile
import uuid

# Must be set before any observability_platform module is imported.
_TMP_DB = os.path.join(tempfile.gettempdir(), f"observability_platform_test_{uuid.uuid4().hex}.db").replace("\\", "/")
os.environ["DATABASE_URL"] = f"sqlite+aiosqlite:///{_TMP_DB}"
os.environ["SECRET_KEY"] = "x" * 32
os.environ["APP_ENV"] = "test"

import pytest_asyncio

import observability_platform.models  # noqa: F401 — populate Base.metadata
from observability_platform.database.session import async_session_factory, dispose_engine, init_models
from observability_platform.repositories.registry import RepositoryRegistry


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
    """Rollback-isolated by default — BUT `AlertEvaluationService.
    fire_or_update`/`auto_resolve_if_healed` deliberately call
    `self.repos.session.commit()` mid-method (a per-dedup-key
    `asyncio.Lock` held across the commit, same pattern as
    `EditSessionService.start_session` in the Collaboration Platform).
    A test that calls `AlertEvaluationService.evaluate_rule` (or either
    of those methods directly) through this fixture durably commits
    everything written earlier in that same test, bypassing this
    teardown's rollback — confirmed the hard way here too: the alerting
    tests originally reused generic metric names ("cpu_usage",
    "latency_ms") already used by `tests/metrics/test_metrics.py`, and
    the leaked committed rows broke that file's exact-count assertions
    when the suite ran in full (passed in isolation, failed in
    collection order — the same signature as the Collaboration
    Platform's `_OBS_USER` incident). Fixed by giving the alerting
    tests their own metric-name prefix (`alert_cpu_usage`,
    `alert_latency_ms`) — use a unique identifier, never a generic one
    another file's exact-count assertion might depend on staying
    isolated, any time a test exercises a commit-spanning method."""
    async with async_session_factory() as session:
        yield session
        await session.rollback()


@pytest_asyncio.fixture
async def repos(db_session) -> RepositoryRegistry:
    return RepositoryRegistry(db_session)
