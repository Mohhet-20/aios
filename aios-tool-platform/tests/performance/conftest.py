"""Fixtures for genuine concurrency/stress tests: many *independent*
AsyncSession/RepositoryRegistry/ToolExecutionEngine trios racing against
the same underlying WAL-mode SQLite file — the shape real concurrent API
traffic takes (every FastAPI request gets a fresh session; see
`dependencies/dependencies.py`), as opposed to the rest of the suite's
single shared `repos` fixture. Setup data (workspace/tool/published
version) is created through its own session and *committed* so the
independent sessions used during the actual test body can see it — the
main suite's `repos` fixture never commits (it rolls back after each
test), which is correct for isolation there but would make
committed-data invisible to a second, concurrently-opened connection
here.

Some tests in this suite instead use the shared `repos` fixture directly
(no cross-session concurrency needed for those) via the `workspace`/
`tool_service`/`version_service` fixtures defined below, mirroring
`tests/execution/conftest.py`'s pattern locally so this directory stays
self-contained."""
from __future__ import annotations

import uuid

import pytest

from tool_platform.database.session import async_session_factory
from tool_platform.models.workspace import WorkspaceModel
from tool_platform.repositories.registry import RepositoryRegistry
from tool_platform.tool_core.tool_service import ToolService
from tool_platform.tool_core.version_service import ToolVersionService
from tool_platform.tool_execution.engine import ToolExecutionEngine
from tool_platform.tool_execution.registry import ConnectorRegistry, build_default_connector_registry


def new_repos() -> RepositoryRegistry:
    return RepositoryRegistry(async_session_factory())


def new_engine(repos: RepositoryRegistry, connectors: ConnectorRegistry | None = None, **kwargs) -> ToolExecutionEngine:
    return ToolExecutionEngine(repos, connectors or build_default_connector_registry(), **kwargs)


async def make_committed_workspace(*, name="Perf Co") -> WorkspaceModel:
    repos = new_repos()
    try:
        ws = await repos.workspaces.add(WorkspaceModel(name=name, organization_id=f"org-{uuid.uuid4().hex[:8]}", slug=f"perf-{uuid.uuid4().hex[:8]}"))
        await repos.session.commit()
        return ws
    finally:
        await repos.session.close()


async def make_committed_tool(workspace_id: str, *, name="Perf Tool", connector_key="echo", sensitivity_level="normal"):
    repos = new_repos()
    try:
        tool_service = ToolService(repos)
        version_service = ToolVersionService(repos)
        tool = await tool_service.create_tool(workspace_id, name=name, owner_id="u1", category="custom", organization_id="org-1")
        draft = await version_service.get_or_create_draft(tool.id, created_by="u1")
        await version_service.update_draft(
            draft.id, connector_key=connector_key, sensitivity_level=sensitivity_level,
            default_max_retries=0, default_timeout_seconds=10, default_retry_backoff_seconds=0.01,
        )
        await version_service.publish_version(draft.id)
        await repos.session.commit()
        return await tool_service.get_tool(tool.id)
    finally:
        await repos.session.close()


@pytest.fixture
async def workspace(repos):
    return await repos.workspaces.add(WorkspaceModel(name="Perf Fixture Co", organization_id="org-1", slug="perf-fixture-co"))


@pytest.fixture
def tool_service(repos):
    return ToolService(repos)


@pytest.fixture
def version_service(repos):
    return ToolVersionService(repos)
