import pytest

from memory_platform.domain.enums import Role
from memory_platform.governance.audit_service import AuditService
from memory_platform.governance.compliance import resource_compliance_snapshot, workspace_compliance_snapshot
from memory_platform.governance.rbac_service import RBACService
from memory_platform.memory_core.memory_service import MemoryService
from memory_platform.memory_registry.seed_types import seed_builtin_memory_types
from memory_platform.domain.enums import MemoryType
from memory_platform.models.workspace import WorkspaceModel


async def _workspace(repos):
    return await repos.workspaces.add(WorkspaceModel(id="ws-1", name="Acme", slug="acme", organization_id="org-1"))


@pytest.mark.asyncio
async def test_audit_service_records_and_retrieves(repos):
    await _workspace(repos)
    audit = AuditService(repos)
    await audit.record(actor_id="user-1", action="knowledge_base.create", resource_type="knowledge_base", resource_id="kb-1")
    await audit.record_access_denied(actor_id="user-2", resource_type="knowledge_base", resource_id="kb-1", reason="insufficient role")

    trail = await audit.get_audit_trail("knowledge_base", "kb-1")
    assert len(trail) == 2
    actions = {t.action for t in trail}
    assert actions == {"knowledge_base.create", "access.denied"}


@pytest.mark.asyncio
async def test_resource_compliance_snapshot(repos):
    await _workspace(repos)
    rbac = RBACService(repos)
    audit = AuditService(repos)
    await rbac.grant_role(principal_id="user-1", resource_type="knowledge_base", resource_id="kb-1", role=Role.ADMIN, granted_by="owner-1")
    await audit.record(actor_id="user-1", action="knowledge_base.create", resource_type="knowledge_base", resource_id="kb-1")

    snapshot = await resource_compliance_snapshot(repos, "knowledge_base", "kb-1")
    assert snapshot.grant_count == 1
    assert snapshot.audit_event_count == 1


@pytest.mark.asyncio
async def test_workspace_compliance_snapshot(repos):
    await seed_builtin_memory_types(repos)
    await _workspace(repos)
    rbac = RBACService(repos)
    mem = MemoryService(repos)
    await rbac.grant_role(principal_id="user-1", resource_type="workspace", resource_id="ws-1", role=Role.ADMIN, granted_by="owner-1")
    await mem.create(workspace_id="ws-1", memory_type=MemoryType.SEMANTIC, scope_type="user", scope_id="u-1", content="a fact")

    snapshot = await workspace_compliance_snapshot(repos, "ws-1")
    assert snapshot.workspace_level_grant_count == 1
    assert snapshot.active_memory_entry_count == 1
