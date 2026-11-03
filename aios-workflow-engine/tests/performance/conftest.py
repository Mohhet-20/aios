"""Fixtures for genuine concurrency/stress tests: many *independent*
AsyncSession/RepositoryRegistry/ExecutionEngine trios racing against the
same underlying WAL-mode SQLite file — the shape real concurrent API
traffic takes (each FastAPI request gets its own fresh session per
`workflow_api/dependencies.py`), as opposed to the rest of the suite's
single shared `repos` fixture. Setup data (workspace/workflow/published
version) is created through its own session and *committed* so the
independent sessions used during the actual test body can see it —
the main suite's `repos` fixture never commits (it rolls back after
each test), which is correct for isolation there but would make
committed-data invisible to a second, concurrently-opened connection
here."""
from __future__ import annotations

import uuid

from workflow_platform.ai_bridges.reference_bridges import build_reference_bridge_set
from workflow_platform.database.session import async_session_factory
from workflow_platform.models.workspace import WorkspaceModel
from workflow_platform.repositories.registry import RepositoryRegistry
from workflow_platform.workflow_core.version_service import WorkflowVersionService
from workflow_platform.workflow_core.workflow_service import WorkflowService
from workflow_platform.workflow_engine.engine import ExecutionEngine
from workflow_platform.workflow_engine.registry import build_default_handler_registry


def new_repos() -> RepositoryRegistry:
    return RepositoryRegistry(async_session_factory())


def new_engine(repos: RepositoryRegistry, *, sleep_fn=None) -> ExecutionEngine:
    bridges = build_reference_bridge_set()
    handlers = build_default_handler_registry(bridges=bridges)
    kwargs = {"bridges": bridges}
    if sleep_fn is not None:
        kwargs["sleep_fn"] = sleep_fn
    return ExecutionEngine(repos, handlers, **kwargs)


async def make_committed_workspace(*, name="Perf Co") -> WorkspaceModel:
    """Deliberately does NOT seed node_definitions: that table is global,
    process-wide reference data (see `node_library/registry.py`), and
    committing rows into it here would leak across test *files* within
    the same pytest run (unlike everything else in this suite, which
    isolates via a per-test rollback). The linear/approval graphs these
    performance tests use don't need node_definitions to exist — every
    lookup in `ExecutionEngine._dispatch_node`/`rollback` degrades to a
    sane default (timeout=300s, retries=0, not compensable) when a
    definition is missing, by design."""
    repos = new_repos()
    try:
        ws = await repos.workspaces.add(WorkspaceModel(name=name, organization_id=f"org-{uuid.uuid4().hex[:8]}", slug=f"perf-{uuid.uuid4().hex[:8]}"))
        await repos.session.commit()
        return ws
    finally:
        await repos.session.close()


async def make_committed_linear_workflow(workspace_id: str, *, name="Perf WF", seconds: float = 0.0):
    """A trivial start -> delay(seconds) -> end workflow, published, committed."""
    repos = new_repos()
    try:
        workflow_service = WorkflowService(repos)
        version_service = WorkflowVersionService(repos)
        wf = await workflow_service.create_workflow(workspace_id, name=name, owner_id="u1", category="automation")
        draft = await version_service.get_or_create_draft(wf.id, created_by="u1")
        await version_service.add_node(draft.id, node_key="start", node_type="start", name="Start")
        await version_service.add_node(draft.id, node_key="delay", node_type="delay", name="Delay", config={"seconds": seconds})
        await version_service.add_node(draft.id, node_key="end", node_type="end", name="End")
        await version_service.add_edge(draft.id, source_node_key="start", target_node_key="delay")
        await version_service.add_edge(draft.id, source_node_key="delay", target_node_key="end")
        await version_service.publish_version(draft.id)
        await repos.session.commit()
        return wf
    finally:
        await repos.session.close()
