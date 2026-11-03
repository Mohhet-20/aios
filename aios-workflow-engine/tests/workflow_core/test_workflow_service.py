import pytest

from workflow_platform.core.exceptions import InvalidTransitionError, ValidationError
from workflow_platform.core.pagination import PaginationParams
from workflow_platform.models.workspace import WorkspaceModel
from workflow_platform.workflow_core.workflow_service import WorkflowService


@pytest.fixture
async def workspace(repos):
    ws = await repos.workspaces.add(WorkspaceModel(name="Acme", organization_id="org-1", slug="acme"))
    return ws


@pytest.mark.asyncio
async def test_create_workflow_generates_slug(repos, workspace):
    svc = WorkflowService(repos)
    wf = await svc.create_workflow(workspace.id, name="My Great Workflow", owner_id="u1", category="automation")
    assert wf.slug == "my-great-workflow"
    assert wf.status == "draft"


@pytest.mark.asyncio
async def test_duplicate_slug_rejected(repos, workspace):
    svc = WorkflowService(repos)
    await svc.create_workflow(workspace.id, name="Dup", owner_id="u1", category="automation")
    with pytest.raises(ValidationError):
        await svc.create_workflow(workspace.id, name="Dup", owner_id="u1", category="automation")


@pytest.mark.asyncio
async def test_update_rejects_unknown_field(repos, workspace):
    svc = WorkflowService(repos)
    wf = await svc.create_workflow(workspace.id, name="Editable", owner_id="u1", category="automation")
    with pytest.raises(ValidationError):
        await svc.update_workflow(wf.id, status="active")


@pytest.mark.asyncio
async def test_update_allowed_field(repos, workspace):
    svc = WorkflowService(repos)
    wf = await svc.create_workflow(workspace.id, name="Editable", owner_id="u1", category="automation")
    updated = await svc.update_workflow(wf.id, description="new description", priority="high")
    assert updated.description == "new description"
    assert updated.priority == "high"


@pytest.mark.asyncio
async def test_publish_requires_version_id(repos, workspace):
    svc = WorkflowService(repos)
    wf = await svc.create_workflow(workspace.id, name="NeedsVersion", owner_id="u1", category="automation")
    with pytest.raises(ValidationError):
        await svc.publish(wf.id, "")


@pytest.mark.asyncio
async def test_publish_then_pause_then_resume(repos, workspace):
    svc = WorkflowService(repos)
    wf = await svc.create_workflow(workspace.id, name="Lifecycle", owner_id="u1", category="automation")
    published = await svc.publish(wf.id, "v1")
    assert published.status == "active"
    assert published.current_version_id == "v1"

    paused = await svc.pause(wf.id)
    assert paused.status == "paused"

    resumed = await svc.resume(wf.id)
    assert resumed.status == "active"


@pytest.mark.asyncio
async def test_cannot_resume_a_draft_workflow(repos, workspace):
    svc = WorkflowService(repos)
    wf = await svc.create_workflow(workspace.id, name="StillDraft", owner_id="u1", category="automation")
    with pytest.raises(InvalidTransitionError):
        await svc.resume(wf.id)


@pytest.mark.asyncio
async def test_list_workflows_paginated(repos, workspace):
    svc = WorkflowService(repos)
    for i in range(3):
        await svc.create_workflow(workspace.id, name=f"WF {i}", owner_id="u1", category="automation")
    page = await svc.list_workflows(workspace.id, PaginationParams(page=1, page_size=2))
    assert page.total == 3
    assert len(page.items) == 2
    assert page.total_pages == 2
