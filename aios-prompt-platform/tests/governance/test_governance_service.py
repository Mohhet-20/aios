import pytest

from prompt_platform.core.exceptions import AuthorizationError
from prompt_platform.domain.enums import Permission, Role
from prompt_platform.prompt_engine.prompt_service import PromptService
from prompt_platform.prompt_governance.governance_service import GovernanceService
from prompt_platform.models.workspace import PromptProjectModel, PromptWorkspaceModel


async def _seed(repos, *, owner_id="owner1"):
    ws = await repos.workspaces.add(PromptWorkspaceModel(name="WS", slug="ws-gov", organization_id="org1"))
    proj = await repos.projects.add(PromptProjectModel(workspace_id=ws.id, name="Proj", slug="proj-gov"))
    prompt_svc = PromptService(repos)
    prompt = await prompt_svc.create_prompt(workspace_id=ws.id, project_id=proj.id, name="QA Prompt", owner_id=owner_id)
    return ws, proj, prompt


@pytest.mark.asyncio
async def test_owner_has_implicit_owner_role_and_full_permissions(repos):
    ws, proj, prompt = await _seed(repos, owner_id="owner1")
    gov = GovernanceService(repos)
    role = await gov.effective_role_for_prompt("owner1", prompt)
    assert role == Role.OWNER
    assert await gov.check_permission_on_prompt("owner1", prompt, Permission.PROMPT_DELETE) is True


@pytest.mark.asyncio
async def test_stranger_has_no_role_and_no_permissions(repos):
    ws, proj, prompt = await _seed(repos)
    gov = GovernanceService(repos)
    role = await gov.effective_role_for_prompt("stranger1", prompt)
    assert role is None
    assert await gov.check_permission_on_prompt("stranger1", prompt, Permission.PROMPT_READ) is False
    with pytest.raises(AuthorizationError):
        await gov.require_permission_on_prompt("stranger1", prompt, Permission.PROMPT_READ)


@pytest.mark.asyncio
async def test_explicit_prompt_grant_gives_permission(repos):
    ws, proj, prompt = await _seed(repos)
    gov = GovernanceService(repos)
    await gov.grant_permission("prompt", prompt.id, "editor1", Role.EDITOR, granted_by="owner1")
    assert await gov.check_permission_on_prompt("editor1", prompt, Permission.VERSION_CREATE) is True
    assert await gov.check_permission_on_prompt("editor1", prompt, Permission.VERSION_APPROVE) is False


@pytest.mark.asyncio
async def test_workspace_level_grant_applies_to_prompt(repos):
    ws, proj, prompt = await _seed(repos)
    gov = GovernanceService(repos)
    await gov.grant_permission("workspace", ws.id, "viewer1", Role.VIEWER, granted_by="owner1")
    role = await gov.effective_role_for_prompt("viewer1", prompt)
    assert role == Role.VIEWER
    assert await gov.check_permission_on_prompt("viewer1", prompt, Permission.PROMPT_READ) is True


@pytest.mark.asyncio
async def test_prompt_level_grant_takes_precedence_over_workspace(repos):
    ws, proj, prompt = await _seed(repos)
    gov = GovernanceService(repos)
    await gov.grant_permission("workspace", ws.id, "u1", Role.VIEWER, granted_by="owner1")
    await gov.grant_permission("prompt", prompt.id, "u1", Role.ADMIN, granted_by="owner1")
    role = await gov.effective_role_for_prompt("u1", prompt)
    assert role == Role.ADMIN


@pytest.mark.asyncio
async def test_revoke_permission_removes_access(repos):
    ws, proj, prompt = await _seed(repos)
    gov = GovernanceService(repos)
    grant = await gov.grant_permission("prompt", prompt.id, "editor1", Role.EDITOR, granted_by="owner1")
    await gov.revoke_permission(grant.id, actor_id="owner1")
    role = await gov.effective_role_for_prompt("editor1", prompt)
    assert role is None


@pytest.mark.asyncio
async def test_set_sensitive_requires_workspace_manage_permission(repos):
    ws, proj, prompt = await _seed(repos)
    gov = GovernanceService(repos)
    with pytest.raises(AuthorizationError):
        await gov.set_sensitive(prompt.id, True, actor_id="stranger1")

    updated = await gov.set_sensitive(prompt.id, True, actor_id="owner1")
    assert updated.sensitive is True


@pytest.mark.asyncio
async def test_sensitive_prompt_blocks_low_privilege_access(repos):
    ws, proj, prompt = await _seed(repos)
    gov = GovernanceService(repos)
    await gov.set_sensitive(prompt.id, True, actor_id="owner1")
    await gov.grant_permission("prompt", prompt.id, "viewer1", Role.VIEWER, granted_by="owner1")

    prompt = await repos.prompts.get(prompt.id)
    with pytest.raises(AuthorizationError):
        await gov.assert_access_to_sensitive_prompt("viewer1", prompt)

    # Owner (implicit OWNER role) still has access.
    await gov.assert_access_to_sensitive_prompt("owner1", prompt)


@pytest.mark.asyncio
async def test_audit_trail_records_governance_actions(repos):
    ws, proj, prompt = await _seed(repos)
    gov = GovernanceService(repos)
    await gov.grant_permission("prompt", prompt.id, "editor1", Role.EDITOR, granted_by="owner1")
    await gov.set_sensitive(prompt.id, True, actor_id="owner1")

    trail = await gov.audit_trail("prompt", prompt.id)
    actions = {entry.action for entry in trail}
    assert "permission_granted" in actions
    assert "sensitive_flag_changed" in actions


@pytest.mark.asyncio
async def test_compliance_report_summarizes_prompt_state(repos):
    ws, proj, prompt = await _seed(repos)
    gov = GovernanceService(repos)
    await gov.grant_permission("prompt", prompt.id, "editor1", Role.EDITOR, granted_by="owner1")

    report = await gov.compliance_report(prompt.id)
    assert report["owner_id"] == "owner1"
    assert report["explicit_grant_count"] == 1
    assert report["has_production_version"] is False
    assert report["total_version_count"] == 0
