"""TenantIsolationGuard: the single place that asserts one tenant
cannot read or write another's data. This platform's default tenancy
model is a shared database with row-level isolation — every tenant-
scoped table carries an `organization_id` (or, transitively, a
`workspace_id`/`project_id` that resolves back to one) foreign key,
and every service method that loads a resource by id is expected to
call one of these assertions before acting on it. A "dedicated"
tenancy model (separate database/schema per enterprise tenant) is a
deployment-time infrastructure decision this codebase deliberately
doesn't hardcode a stance on — nothing here assumes a shared
connection pool, so routing a specific `organization_id` to a
dedicated engine/session later would slot in at the session-factory
layer without touching this guard."""
from __future__ import annotations

from identity_platform.core.exceptions import TenantIsolationError
from identity_platform.models.project import ProjectModel
from identity_platform.models.workspace import WorkspaceModel


class TenantIsolationGuard:
    @staticmethod
    def assert_organization_match(resource_organization_id: str | None, expected_organization_id: str) -> None:
        if resource_organization_id != expected_organization_id:
            raise TenantIsolationError(
                f"resource belongs to organization '{resource_organization_id}', not '{expected_organization_id}'"
            )

    @staticmethod
    def assert_workspace_in_organization(workspace: WorkspaceModel, organization_id: str) -> None:
        TenantIsolationGuard.assert_organization_match(workspace.organization_id, organization_id)

    @staticmethod
    def assert_project_in_workspace(project: ProjectModel, workspace_id: str) -> None:
        if project.workspace_id != workspace_id:
            raise TenantIsolationError(f"project '{project.id}' belongs to workspace '{project.workspace_id}', not '{workspace_id}'")

    @staticmethod
    def assert_project_in_organization(project: ProjectModel, organization_id: str) -> None:
        TenantIsolationGuard.assert_organization_match(project.organization_id, organization_id)
