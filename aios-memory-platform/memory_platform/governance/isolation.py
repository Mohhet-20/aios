"""Workspace and organization isolation guards — every multi-tenant read/
write in this platform should pass through these before touching a
resource, so a bug elsewhere (a missing `workspace_id` filter in a new
query, say) doesn't silently leak one tenant's data into another's
response. Deliberately simple, explicit assertions rather than a query-
rewriting middleware, so the check is visible at the call site.
"""
from __future__ import annotations

from memory_platform.core.exceptions import AuthorizationError
from memory_platform.models.workspace import WorkspaceModel


def enforce_workspace_isolation(resource_workspace_id: str, expected_workspace_id: str, *, resource_type: str = "resource") -> None:
    if resource_workspace_id != expected_workspace_id:
        raise AuthorizationError(f"{resource_type} belongs to workspace '{resource_workspace_id}', not '{expected_workspace_id}' — cross-workspace access denied")


def enforce_organization_isolation(workspace: WorkspaceModel, expected_organization_id: str) -> None:
    if workspace.organization_id != expected_organization_id:
        raise AuthorizationError(f"workspace '{workspace.id}' belongs to organization '{workspace.organization_id}', not '{expected_organization_id}' — cross-organization access denied")
