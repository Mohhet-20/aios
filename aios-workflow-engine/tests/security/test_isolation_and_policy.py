import pytest

from workflow_platform.core.exceptions import AuthorizationError, ValidationError
from workflow_platform.domain.enums import Role
from workflow_platform.models.workspace import WorkspaceModel
from workflow_platform.security.isolation import IsolationGuard
from workflow_platform.security.policy_service import ApprovalPolicyService, ExecutionPolicyService
from workflow_platform.security.rbac_service import RBACService
from workflow_platform.workflow_core.workflow_service import WorkflowService


@pytest.mark.asyncio
async def test_isolation_guard_rejects_cross_organization_workspace(repos):
    ws = await repos.workspaces.add(WorkspaceModel(name="Org A Co", organization_id="org-a", slug="org-a-co"))
    IsolationGuard.assert_workspace_in_organization(ws, "org-a")  # should not raise
    with pytest.raises(AuthorizationError):
        IsolationGuard.assert_workspace_in_organization(ws, "org-b")


@pytest.mark.asyncio
async def test_isolation_guard_rejects_cross_workspace_resource(repos):
    ws1 = await repos.workspaces.add(WorkspaceModel(name="WS1", organization_id="org-1", slug="ws1"))
    ws2 = await repos.workspaces.add(WorkspaceModel(name="WS2", organization_id="org-1", slug="ws2"))
    wf_service = WorkflowService(repos)
    wf = await wf_service.create_workflow(ws1.id, name="WF", owner_id="u1", category="automation")

    IsolationGuard.assert_resource_in_workspace(wf, ws1.id)  # should not raise
    with pytest.raises(AuthorizationError):
        IsolationGuard.assert_resource_in_workspace(wf, ws2.id)


@pytest.mark.asyncio
async def test_execution_policy_requires_execute_permission(repos):
    ws = await repos.workspaces.add(WorkspaceModel(name="Policy Co", organization_id="org-1", slug="policy-co"))
    wf_service = WorkflowService(repos)
    wf = await wf_service.create_workflow(ws.id, name="Gated WF", owner_id="u1", category="automation")

    rbac = RBACService(repos)
    policy = ExecutionPolicyService(rbac)

    with pytest.raises(AuthorizationError):
        await policy.authorize_start_execution("stranger", wf)

    await rbac.grant("operator-1", "workspace", ws.id, Role.OPERATOR, granted_by="admin")
    await policy.authorize_start_execution("operator-1", wf)  # should not raise


def test_approval_policy_enforces_minimum_chain_length_by_sensitivity():
    policy = ApprovalPolicyService()
    assert policy.required_chain_length("normal") == 1
    assert policy.required_chain_length("high") == 2
    assert policy.required_chain_length("critical") == 3

    policy.validate_chain([["mgr-1"]], "normal")  # ok
    with pytest.raises(ValidationError):
        policy.validate_chain([["mgr-1"]], "critical")

    policy.validate_chain([["mgr-1"], ["fin-1"], ["cfo-1"]], "critical")  # ok
