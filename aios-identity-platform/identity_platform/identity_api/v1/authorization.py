"""RBAC: custom-role CRUD, role assignment/revocation, and the
permission-check/effective-permissions read endpoints every other
platform's middleware calls against."""
from __future__ import annotations

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from identity_platform.authorization.assignment_service import RoleAssignmentService
from identity_platform.authorization.authorization_service import AuthorizationService
from identity_platform.authorization.role_service import RoleService
from identity_platform.dependencies.dependencies import (
    get_authorization_service,
    get_role_assignment_service,
    get_role_service,
)
from identity_platform.domain.enums import RoleScopeType
from identity_platform.identity_api.serialization import to_dict, to_dict_list

router = APIRouter(prefix="/authorization", tags=["authorization"])


class CreateRoleRequest(BaseModel):
    organization_id: str
    name: str
    slug: str
    scope_type: RoleScopeType
    permissions: list[str]
    description: str | None = None


@router.post("/roles", status_code=201)
async def create_role(body: CreateRoleRequest, service: RoleService = Depends(get_role_service)):
    role = await service.create_custom_role(
        body.organization_id, name=body.name, slug=body.slug, scope_type=body.scope_type,
        permissions=body.permissions, description=body.description,
    )
    return to_dict(role)


class UpdateRolePermissionsRequest(BaseModel):
    permissions: list[str]


@router.put("/roles/{role_id}/permissions")
async def update_role_permissions(role_id: str, body: UpdateRolePermissionsRequest, service: RoleService = Depends(get_role_service)):
    return to_dict(await service.update_permissions(role_id, body.permissions))


@router.delete("/roles/{role_id}", status_code=204)
async def delete_role(role_id: str, service: RoleService = Depends(get_role_service)):
    await service.delete_custom_role(role_id)


@router.get("/organizations/{organization_id}/roles")
async def list_available_roles(organization_id: str, service: RoleService = Depends(get_role_service)):
    return to_dict_list(await service.list_available_for_organization(organization_id))


class AssignRoleRequest(BaseModel):
    principal_type: str
    principal_id: str
    role_id: str
    scope_type: RoleScopeType
    scope_id: str
    granted_by: str


@router.post("/assignments", status_code=201)
async def assign_role(body: AssignRoleRequest, service: RoleAssignmentService = Depends(get_role_assignment_service)):
    assignment = await service.assign_role(
        principal_type=body.principal_type, principal_id=body.principal_id, role_id=body.role_id,
        scope_type=body.scope_type, scope_id=body.scope_id, granted_by=body.granted_by,
    )
    return to_dict(assignment)


@router.post("/assignments/{assignment_id}/revoke")
async def revoke_assignment(assignment_id: str, service: RoleAssignmentService = Depends(get_role_assignment_service)):
    return to_dict(await service.revoke_assignment(assignment_id))


@router.get("/principals/{principal_type}/{principal_id}/assignments")
async def list_assignments_for_principal(principal_type: str, principal_id: str, service: RoleAssignmentService = Depends(get_role_assignment_service)):
    return to_dict_list(await service.list_for_principal(principal_type, principal_id))


@router.get("/check")
async def check_permission(
    principal_type: str, principal_id: str, permission_key: str, scope_type: RoleScopeType, scope_id: str,
    service: AuthorizationService = Depends(get_authorization_service),
):
    allowed = await service.has_permission(
        principal_type=principal_type, principal_id=principal_id, permission_key=permission_key,
        scope_type=scope_type, scope_id=scope_id,
    )
    return {"allowed": allowed}


@router.get("/effective-permissions")
async def effective_permissions(
    principal_type: str, principal_id: str, scope_type: RoleScopeType, scope_id: str,
    service: AuthorizationService = Depends(get_authorization_service),
):
    return {"permissions": sorted(await service.effective_permissions(
        principal_type=principal_type, principal_id=principal_id, scope_type=scope_type, scope_id=scope_id,
    ))}
