"""Security & Governance: RBAC role assignment, doc visibility checks,
and version protection status."""
from __future__ import annotations

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from docs_platform.dependencies.dependencies import (
    get_current_tenant_id,
    get_doc_page_service,
    get_governance_service,
    get_role_assignment_service,
    get_visibility_service,
)
from docs_platform.doc_api.serialization import to_dict_list
from docs_platform.documentation.doc_page_service import DocPageService
from docs_platform.core.exceptions import VersionProtectedError
from docs_platform.security.governance_service import GovernanceService
from docs_platform.security.role_assignment_service import RoleAssignmentService
from docs_platform.security.visibility_service import VisibilityService

router = APIRouter(prefix="/roles", tags=["security"])
visibility_router = APIRouter(prefix="/visibility", tags=["security"])
governance_router = APIRouter(prefix="/governance", tags=["security"])


class AssignRoleRequest(BaseModel):
    user_id: str
    role: str
    scope_ref: str | None = None


@router.post("", status_code=201)
async def assign_role(
    body: AssignRoleRequest, tenant_id: str = Depends(get_current_tenant_id), service: RoleAssignmentService = Depends(get_role_assignment_service),
):
    assignment = await service.assign_role(tenant_id, **body.model_dump())
    return {
        "id": assignment.id, "tenant_id": assignment.tenant_id, "user_id": assignment.user_id,
        "role": assignment.role, "scope_ref": assignment.scope_ref,
    }


@router.get("/by-user/{user_id}")
async def list_roles_for_user(
    user_id: str, tenant_id: str = Depends(get_current_tenant_id), service: RoleAssignmentService = Depends(get_role_assignment_service),
):
    return to_dict_list(await service.list_for_user(tenant_id, user_id))


@visibility_router.get("/can-view/{page_id}")
async def can_view_page(
    page_id: str, user_id: str | None = None,
    tenant_id: str = Depends(get_current_tenant_id),
    page_service: DocPageService = Depends(get_doc_page_service),
    visibility_service: VisibilityService = Depends(get_visibility_service),
):
    page = await page_service.get_or_404(tenant_id, page_id)
    allowed = await visibility_service.can_view(tenant_id, visibility=page.visibility, user_id=user_id, space_id=page.space_id)
    return {"page_id": page_id, "user_id": user_id, "can_view": allowed}


@governance_router.get("/is-editable/{page_id}")
async def is_page_editable(
    page_id: str, tenant_id: str = Depends(get_current_tenant_id),
    page_service: DocPageService = Depends(get_doc_page_service),
    governance_service: GovernanceService = Depends(get_governance_service),
):
    page = await page_service.get_or_404(tenant_id, page_id)
    try:
        governance_service.assert_editable(page)
        editable = True
    except VersionProtectedError:
        editable = False
    return {"page_id": page_id, "status": page.status, "editable": editable}
