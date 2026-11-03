import pytest

from workflow_platform.core.exceptions import ValidationError
from workflow_platform.models.workspace import WorkspaceModel
from workflow_platform.workflow_core.version_service import WorkflowVersionService
from workflow_platform.workflow_core.workflow_service import WorkflowService


@pytest.fixture
async def workflow(repos):
    ws = await repos.workspaces.add(WorkspaceModel(name="Acme2", organization_id="org-1", slug="acme2"))
    wsvc = WorkflowService(repos)
    return await wsvc.create_workflow(ws.id, name="Versioned WF", owner_id="u1", category="automation")


async def _build_valid_graph(vsvc: WorkflowVersionService, version_id: str):
    await vsvc.add_node(version_id, node_key="start", node_type="start", name="Start")
    await vsvc.add_node(version_id, node_key="call_llm", node_type="llm_call", name="Call LLM")
    await vsvc.add_node(version_id, node_key="end", node_type="end", name="End")
    await vsvc.add_edge(version_id, source_node_key="start", target_node_key="call_llm")
    await vsvc.add_edge(version_id, source_node_key="call_llm", target_node_key="end")


@pytest.mark.asyncio
async def test_get_or_create_draft_creates_version_one(repos, workflow):
    vsvc = WorkflowVersionService(repos)
    draft = await vsvc.get_or_create_draft(workflow.id, created_by="u1")
    assert draft.version_number == 1
    assert draft.status == "draft"

    # calling again returns the same draft, not a new one
    draft2 = await vsvc.get_or_create_draft(workflow.id, created_by="u1")
    assert draft2.id == draft.id


@pytest.mark.asyncio
async def test_add_duplicate_node_key_rejected(repos, workflow):
    vsvc = WorkflowVersionService(repos)
    draft = await vsvc.get_or_create_draft(workflow.id, created_by="u1")
    await vsvc.add_node(draft.id, node_key="start", node_type="start", name="Start")
    with pytest.raises(ValidationError):
        await vsvc.add_node(draft.id, node_key="start", node_type="start", name="Start Again")


@pytest.mark.asyncio
async def test_publish_version_validates_graph_and_activates_workflow(repos, workflow):
    vsvc = WorkflowVersionService(repos)
    draft = await vsvc.get_or_create_draft(workflow.id, created_by="u1")
    await _build_valid_graph(vsvc, draft.id)

    published = await vsvc.publish_version(draft.id)
    assert published.status == "published"

    updated_workflow = await repos.workflows.get_or_404(workflow.id)
    assert updated_workflow.status == "active"
    assert updated_workflow.current_version_id == published.id


@pytest.mark.asyncio
async def test_publish_rejects_invalid_graph(repos, workflow):
    vsvc = WorkflowVersionService(repos)
    draft = await vsvc.get_or_create_draft(workflow.id, created_by="u1")
    await vsvc.add_node(draft.id, node_key="start", node_type="start", name="Start")
    # no END node -> should fail validation
    with pytest.raises(ValidationError):
        await vsvc.publish_version(draft.id)


@pytest.mark.asyncio
async def test_cannot_edit_published_version(repos, workflow):
    vsvc = WorkflowVersionService(repos)
    draft = await vsvc.get_or_create_draft(workflow.id, created_by="u1")
    await _build_valid_graph(vsvc, draft.id)
    await vsvc.publish_version(draft.id)

    with pytest.raises(ValidationError):
        await vsvc.add_node(draft.id, node_key="extra", node_type="llm_call", name="Extra")


@pytest.mark.asyncio
async def test_new_draft_after_publish_inherits_prior_graph(repos, workflow):
    vsvc = WorkflowVersionService(repos)
    draft_v1 = await vsvc.get_or_create_draft(workflow.id, created_by="u1")
    await _build_valid_graph(vsvc, draft_v1.id)
    await vsvc.publish_version(draft_v1.id)

    draft_v2 = await vsvc.get_or_create_draft(workflow.id, created_by="u1")
    assert draft_v2.version_number == 2
    nodes, edges = await vsvc.get_graph(draft_v2.id)
    assert {n.node_key for n in nodes} == {"start", "call_llm", "end"}
    assert len(edges) == 2


@pytest.mark.asyncio
async def test_remove_node_also_removes_incident_edges(repos, workflow):
    vsvc = WorkflowVersionService(repos)
    draft = await vsvc.get_or_create_draft(workflow.id, created_by="u1")
    await _build_valid_graph(vsvc, draft.id)

    await vsvc.remove_node(draft.id, "call_llm")
    nodes, edges = await vsvc.get_graph(draft.id)
    assert {n.node_key for n in nodes} == {"start", "end"}
    assert edges == []


@pytest.mark.asyncio
async def test_in_flight_execution_keeps_old_version_after_republish(repos, workflow):
    """Simulates the production-correctness scenario the module docstring
    calls out: an execution pinned to v1 must be unaffected by v2 publishing."""
    vsvc = WorkflowVersionService(repos)
    draft_v1 = await vsvc.get_or_create_draft(workflow.id, created_by="u1")
    await _build_valid_graph(vsvc, draft_v1.id)
    v1 = await vsvc.publish_version(draft_v1.id)

    # "execution" captures v1.id here, exactly like ExecutionModel.workflow_version_id would
    pinned_version_id = v1.id

    draft_v2 = await vsvc.get_or_create_draft(workflow.id, created_by="u1")
    await vsvc.add_node(draft_v2.id, node_key="extra", node_type="llm_call", name="Extra")
    await vsvc.add_edge(draft_v2.id, source_node_key="call_llm", target_node_key="extra")
    await vsvc.remove_edge(
        (await repos.workflow_edges.list_for_version(draft_v2.id))[1].id
    )  # remove the old call_llm->end edge, route through extra instead
    await vsvc.add_edge(draft_v2.id, source_node_key="extra", target_node_key="end")
    await vsvc.publish_version(draft_v2.id)

    # the pinned version's graph must be untouched
    nodes, _ = await vsvc.get_graph(pinned_version_id)
    assert {n.node_key for n in nodes} == {"start", "call_llm", "end"}
