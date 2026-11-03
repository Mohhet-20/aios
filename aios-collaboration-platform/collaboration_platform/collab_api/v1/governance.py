"""Security & governance: workspace/asset permission grants, share
links, external shares, audit log, and retention policies."""
from __future__ import annotations

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from collaboration_platform.collab_api.serialization import to_dict, to_dict_list
from collaboration_platform.dependencies.dependencies import (
    get_audit_service,
    get_external_share_service,
    get_permission_service,
    get_retention_service,
    get_share_link_service,
)
from collaboration_platform.domain.enums import PrincipalType, SharePermission, WorkspaceRole
from collaboration_platform.governance.audit_service import AuditService
from collaboration_platform.governance.permission_service import PermissionService
from collaboration_platform.governance.retention_service import RetentionService
from collaboration_platform.sharing.sharing_service import ExternalShareService, ShareLinkService

router = APIRouter(prefix="/governance", tags=["governance"])


class GrantWorkspacePermissionRequest(BaseModel):
    principal_type: PrincipalType
    principal_id: str
    role: WorkspaceRole
    granted_by: str | None = None


@router.post("/workspaces/{workspace_id}/permissions", status_code=201)
async def grant_workspace_permission(workspace_id: str, body: GrantWorkspacePermissionRequest, service: PermissionService = Depends(get_permission_service)):
    return to_dict(await service.grant_workspace_permission(workspace_id, body.principal_type, body.principal_id, body.role, granted_by=body.granted_by))


class GrantAssetPermissionRequest(BaseModel):
    principal_type: PrincipalType
    principal_id: str
    role: WorkspaceRole
    granted_by: str | None = None


@router.post("/assets/{asset_id}/permissions", status_code=201)
async def grant_asset_permission(asset_id: str, body: GrantAssetPermissionRequest, service: PermissionService = Depends(get_permission_service)):
    return to_dict(await service.grant_asset_permission(asset_id, body.principal_type, body.principal_id, body.role, granted_by=body.granted_by))


@router.get("/assets/{asset_id}/effective-role/{principal_id}")
async def effective_role(asset_id: str, principal_id: str, service: PermissionService = Depends(get_permission_service)):
    role = await service.effective_role(asset_id, principal_id)
    return {"principal_id": principal_id, "asset_id": asset_id, "role": role.value if role else None}


class CreateShareLinkRequest(BaseModel):
    created_by: str
    permission: SharePermission = SharePermission.VIEW


@router.post("/assets/{asset_id}/share-links", status_code=201)
async def create_share_link(asset_id: str, body: CreateShareLinkRequest, service: ShareLinkService = Depends(get_share_link_service)):
    link, raw_token = await service.create_link(asset_id, created_by=body.created_by, permission=body.permission)
    return {"link": to_dict(link), "token": raw_token}


@router.get("/share-links/resolve/{raw_token}")
async def resolve_share_link(raw_token: str, service: ShareLinkService = Depends(get_share_link_service)):
    return to_dict(await service.resolve_link(raw_token))


@router.post("/share-links/{link_id}/revoke")
async def revoke_share_link(link_id: str, service: ShareLinkService = Depends(get_share_link_service)):
    return to_dict(await service.revoke_link(link_id))


@router.get("/assets/{asset_id}/share-links")
async def list_share_links(asset_id: str, service: ShareLinkService = Depends(get_share_link_service)):
    return to_dict_list(await service.list_for_asset(asset_id))


class InviteExternalRequest(BaseModel):
    email: str
    invited_by: str
    permission: SharePermission = SharePermission.VIEW
    external_sharing_enabled: bool = True


@router.post("/assets/{asset_id}/external-shares", status_code=201)
async def invite_external(asset_id: str, body: InviteExternalRequest, service: ExternalShareService = Depends(get_external_share_service)):
    return to_dict(await service.invite(
        asset_id, body.email, invited_by=body.invited_by, permission=body.permission, external_sharing_enabled=body.external_sharing_enabled,
    ))


@router.post("/external-shares/{external_share_id}/accept")
async def accept_external_share(external_share_id: str, service: ExternalShareService = Depends(get_external_share_service)):
    return to_dict(await service.accept(external_share_id))


@router.post("/external-shares/{external_share_id}/revoke")
async def revoke_external_share(external_share_id: str, service: ExternalShareService = Depends(get_external_share_service)):
    return to_dict(await service.revoke(external_share_id))


@router.get("/assets/{asset_id}/external-shares")
async def list_external_shares(asset_id: str, service: ExternalShareService = Depends(get_external_share_service)):
    return to_dict_list(await service.list_for_asset(asset_id))


@router.get("/workspaces/{workspace_id}/audit-log")
async def list_audit_log(workspace_id: str, action: str | None = None, limit: int = 200, service: AuditService = Depends(get_audit_service)):
    return to_dict_list(await service.list_for_workspace(workspace_id, action=action, limit=limit))


class SetRetentionPolicyRequest(BaseModel):
    resource_type: str
    retain_days: int
    created_by: str
    applies_to_deleted_only: bool = True


@router.put("/workspaces/{workspace_id}/retention-policy")
async def set_retention_policy(workspace_id: str, body: SetRetentionPolicyRequest, service: RetentionService = Depends(get_retention_service)):
    return to_dict(await service.set_policy(
        workspace_id, resource_type=body.resource_type, retain_days=body.retain_days, created_by=body.created_by,
        applies_to_deleted_only=body.applies_to_deleted_only,
    ))


@router.post("/workspaces/{workspace_id}/retention-sweep")
async def sweep_retention(workspace_id: str, service: RetentionService = Depends(get_retention_service)):
    return {"purged_asset_ids": await service.sweep_expired_assets(workspace_id)}
