"""Doc visibility enforcement: internal pages require the requester to
hold at least a 'viewer' role assignment (tenant-wide or scoped to the
page's space); public pages are open to anyone, including anonymous
(role=None) requesters. This mirrors every prior AIOS platform's
"visibility is a read-time filter, not a write-time restriction"
posture — a page's visibility field doesn't change who can edit it,
only who can read it."""
from __future__ import annotations

from docs_platform.core.exceptions import PermissionDeniedError
from docs_platform.security.role_assignment_service import RoleAssignmentService

_PUBLIC = "public"


class VisibilityService:
    def __init__(self, role_service: RoleAssignmentService):
        self.role_service = role_service

    async def can_view(self, tenant_id: str, *, visibility: str, user_id: str | None, space_id: str | None = None) -> bool:
        if visibility == _PUBLIC:
            return True
        if user_id is None:
            return False
        return await self.role_service.has_at_least(tenant_id, user_id, "viewer", scope_ref=space_id)

    async def assert_can_view(self, tenant_id: str, *, visibility: str, user_id: str | None, space_id: str | None = None) -> None:
        if not await self.can_view(tenant_id, visibility=visibility, user_id=user_id, space_id=space_id):
            raise PermissionDeniedError("You do not have permission to view this document")
