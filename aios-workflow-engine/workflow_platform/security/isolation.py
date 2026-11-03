"""IsolationGuard: workspace and organization isolation checks — every
resource in this platform hangs off a `workspace_id` (see `models/
workspace.py`), and every workspace hangs off an `organization_id`.
These guards are the one place that boundary gets enforced, so a future
API layer (Task 95) checks isolation the same way regardless of which
router/endpoint is asking, rather than every endpoint re-deriving its
own notion of "does this resource belong to this caller." """
from __future__ import annotations

from typing import Any

from workflow_platform.core.exceptions import AuthorizationError


class IsolationGuard:
    @staticmethod
    def assert_workspace_in_organization(workspace: Any, organization_id: str) -> None:
        if workspace.organization_id != organization_id:
            raise AuthorizationError(
                f"workspace '{workspace.id}' belongs to organization '{workspace.organization_id}', "
                f"not '{organization_id}'"
            )

    @staticmethod
    def assert_resource_in_workspace(resource: Any, workspace_id: str) -> None:
        resource_workspace_id = getattr(resource, "workspace_id", None)
        if resource_workspace_id != workspace_id:
            raise AuthorizationError(
                f"resource '{getattr(resource, 'id', '?')}' belongs to workspace '{resource_workspace_id}', "
                f"not '{workspace_id}'"
            )
