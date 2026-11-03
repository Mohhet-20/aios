"""Compliance metadata rollups. A per-resource snapshot (grants + audit
trail — both structurally well-defined at the resource level) and a
per-workspace snapshot (grants + active retention policies + memory
counts — everything that genuinely is workspace-scoped in this schema).
Deliberately doesn't claim a workspace-wide audit-event count: audit
entries are keyed by `(resource_type, resource_id)`, not `workspace_id`,
so that number isn't cheaply or honestly derivable without either a
schema change or an expensive join across every resource in the
workspace — flagged here rather than faked.
"""
from __future__ import annotations

from dataclasses import dataclass

from memory_platform.repositories.registry import RepositoryRegistry


@dataclass
class ResourceComplianceSnapshot:
    resource_type: str
    resource_id: str
    grant_count: int
    audit_event_count: int


@dataclass
class WorkspaceComplianceSnapshot:
    workspace_id: str
    workspace_level_grant_count: int
    active_retention_policy_count: int
    active_memory_entry_count: int


async def resource_compliance_snapshot(repos: RepositoryRegistry, resource_type: str, resource_id: str) -> ResourceComplianceSnapshot:
    grants = await repos.permission_grants.list_for_resource(resource_type, resource_id)
    audit_events = await repos.audit_log.list_for_resource(resource_type, resource_id, limit=10_000)
    return ResourceComplianceSnapshot(resource_type=resource_type, resource_id=resource_id, grant_count=len(grants), audit_event_count=len(audit_events))


async def workspace_compliance_snapshot(repos: RepositoryRegistry, workspace_id: str) -> WorkspaceComplianceSnapshot:
    grants = await repos.permission_grants.list_for_resource("workspace", workspace_id)
    policies = await repos.retention_policies.list_active_for_workspace(workspace_id)
    active_count = await repos.memory_entries.count_for_workspace(workspace_id, status="active")
    return WorkspaceComplianceSnapshot(
        workspace_id=workspace_id, workspace_level_grant_count=len(grants), active_retention_policy_count=len(policies), active_memory_entry_count=active_count,
    )
