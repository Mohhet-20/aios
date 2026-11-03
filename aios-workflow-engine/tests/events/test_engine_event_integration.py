"""Verifies the ExecutionEngine <-> EventBus wiring added in Task 88:
workflow lifecycle transitions (start/complete/fail/cancel) publish real
events, recorded as EventModel rows, when an EventBus is attached."""
import asyncio

import pytest

from tests.execution.conftest import publish_graph
from workflow_platform.ai_bridges.reference_bridges import build_reference_bridge_set
from workflow_platform.domain.enums import EventType, ExecutionStatus
from workflow_platform.events.event_bus import EventBus
from workflow_platform.models.execution import ExecutionModel
from workflow_platform.models.workspace import WorkspaceModel
from workflow_platform.node_library.registry import seed_node_definitions
from workflow_platform.workflow_core.version_service import WorkflowVersionService
from workflow_platform.workflow_core.workflow_service import WorkflowService
from workflow_platform.workflow_engine.engine import ExecutionEngine
from workflow_platform.workflow_engine.registry import build_default_handler_registry


@pytest.fixture(autouse=True)
async def _seed(repos):
    await seed_node_definitions(repos)


@pytest.fixture
async def workspace(repos):
    return await repos.workspaces.add(WorkspaceModel(name="Evt Engine Co", organization_id="org-1", slug="evt-engine-co"))


def _engine_with_shared_bus(repos, *, custom_handlers=None):
    bridges = build_reference_bridge_set()
    handlers = build_default_handler_registry(bridges=bridges, custom_handlers=custom_handlers)
    engine = ExecutionEngine(repos, handlers, bridges=bridges, sleep_fn=lambda s: asyncio.sleep(0))
    bus = EventBus(repos, lock=engine._session_lock)
    engine.event_bus = bus
    engine._extra["event_publisher"] = bus.publish
    return engine, bus


@pytest.mark.asyncio
async def test_completed_execution_publishes_started_and_completed_events(repos, workspace):
    wf_service = WorkflowService(repos)
    version_service = WorkflowVersionService(repos)
    wf = await wf_service.create_workflow(workspace.id, name="Evt WF", owner_id="u1", category="automation")
    await publish_graph(
        version_service, wf.id,
        nodes=[
            {"node_key": "start", "node_type": "start", "name": "Start"},
            {"node_key": "end", "node_type": "end", "name": "End"},
        ],
        edges=[{"source_node_key": "start", "target_node_key": "end"}],
    )
    engine, _bus = _engine_with_shared_bus(repos)
    execution = await engine.start_execution(wf.id, triggered_by="u1")
    assert execution.status == ExecutionStatus.COMPLETED.value

    events = await repos.events.list_for_source("execution", execution.id)
    event_types = [e.event_type for e in events]
    assert EventType.WORKFLOW_STARTED.value in event_types
    assert EventType.WORKFLOW_COMPLETED.value in event_types


@pytest.mark.asyncio
async def test_failed_execution_publishes_failed_event(repos, workspace):
    async def always_fails(ctx):
        raise RuntimeError("nope")

    wf_service = WorkflowService(repos)
    version_service = WorkflowVersionService(repos)
    wf = await wf_service.create_workflow(workspace.id, name="Evt Fail WF", owner_id="u1", category="automation")
    await publish_graph(
        version_service, wf.id,
        nodes=[
            {"node_key": "start", "node_type": "start", "name": "Start"},
            {"node_key": "boom", "node_type": "custom", "name": "Boom", "config": {"handler_key": "boom"}},
            {"node_key": "end", "node_type": "end", "name": "End"},
        ],
        edges=[
            {"source_node_key": "start", "target_node_key": "boom"},
            {"source_node_key": "boom", "target_node_key": "end"},
        ],
    )
    engine, _bus = _engine_with_shared_bus(repos, custom_handlers={"boom": always_fails})
    execution = await engine.start_execution(wf.id, triggered_by="u1")
    assert execution.status in (ExecutionStatus.FAILED.value, ExecutionStatus.COMPENSATED.value)

    events = await repos.events.list_for_source("execution", execution.id)
    assert EventType.WORKFLOW_FAILED.value in [e.event_type for e in events]


@pytest.mark.asyncio
async def test_cancel_publishes_cancelled_event(repos, workspace):
    wf_service = WorkflowService(repos)
    version_service = WorkflowVersionService(repos)
    wf = await wf_service.create_workflow(workspace.id, name="Evt Cancel WF", owner_id="u1", category="automation")
    version = await publish_graph(
        version_service, wf.id,
        nodes=[
            {"node_key": "start", "node_type": "start", "name": "Start"},
            {"node_key": "end", "node_type": "end", "name": "End"},
        ],
        edges=[{"source_node_key": "start", "target_node_key": "end"}],
    )
    engine, _bus = _engine_with_shared_bus(repos)
    execution = await repos.executions.add(ExecutionModel(
        workflow_id=wf.id, workflow_version_id=version.id, workspace_id=workspace.id,
        status=ExecutionStatus.PENDING.value, triggered_by="u1",
    ))
    cancelled = await engine.cancel_execution(execution.id)
    assert cancelled.status == ExecutionStatus.CANCELLED.value

    events = await repos.events.list_for_source("execution", execution.id)
    assert EventType.WORKFLOW_CANCELLED.value in [e.event_type for e in events]


@pytest.mark.asyncio
async def test_notification_handler_publishes_through_event_bus(repos, workspace):
    wf_service = WorkflowService(repos)
    version_service = WorkflowVersionService(repos)
    wf = await wf_service.create_workflow(workspace.id, name="Notify WF", owner_id="u1", category="notification")
    await publish_graph(
        version_service, wf.id,
        nodes=[
            {"node_key": "start", "node_type": "start", "name": "Start"},
            {"node_key": "notify", "node_type": "notification", "name": "Notify", "config": {"message": "hello"}},
            {"node_key": "end", "node_type": "end", "name": "End"},
        ],
        edges=[
            {"source_node_key": "start", "target_node_key": "notify"},
            {"source_node_key": "notify", "target_node_key": "end"},
        ],
    )
    engine, _bus = _engine_with_shared_bus(repos)
    execution = await engine.start_execution(wf.id, triggered_by="u1")
    assert execution.status == ExecutionStatus.COMPLETED.value

    events = await repos.events.list_for_workspace(workspace.id, event_type="node_completed")
    assert any(e.payload.get("message") == "hello" for e in events)
