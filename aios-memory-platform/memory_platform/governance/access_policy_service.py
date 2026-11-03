"""AccessPolicyService — combines RBAC with a resource's sensitivity
classification: a RESTRICTED/CONFIDENTIAL item requires a minimum role
even for a principal who otherwise has a broad grant, independent of
whatever coarser permission they hold (mirrors the Prompt Platform's
sensitive-prompt protection: a `sensitive`-flagged resource needs a
minimum role even for read access)."""
from __future__ import annotations

from memory_platform.core.exceptions import AuthorizationError
from memory_platform.domain.enums import Permission, Role, SensitivityLevel
from memory_platform.governance.rbac_service import RBACService

_MINIMUM_ROLE_FOR_SENSITIVITY: dict[SensitivityLevel, Role] = {
    SensitivityLevel.PUBLIC: Role.VIEWER,
    SensitivityLevel.INTERNAL: Role.VIEWER,
    SensitivityLevel.CONFIDENTIAL: Role.OPERATOR,
    SensitivityLevel.RESTRICTED: Role.ADMIN,
}
_ROLE_RANK = {Role.VIEWER: 0, Role.OPERATOR: 1, Role.ADMIN: 2, Role.OWNER: 3}


class AccessPolicyService:
    def __init__(self, rbac: RBACService):
        self.rbac = rbac

    async def enforce_access(
        self, *, principal_id: str, workspace_id: str, permission: Permission, sensitivity_level: SensitivityLevel,
        resource_type: str | None = None, resource_id: str | None = None, owner_id: str | None = None,
    ) -> Role:
        role = await self.rbac.resolve_role(principal_id=principal_id, workspace_id=workspace_id, resource_type=resource_type, resource_id=resource_id, owner_id=owner_id)
        if role is None:
            raise AuthorizationError(f"principal '{principal_id}' has no role in workspace '{workspace_id}'")

        minimum_required = _MINIMUM_ROLE_FOR_SENSITIVITY[sensitivity_level]
        if _ROLE_RANK[role] < _ROLE_RANK[minimum_required]:
            raise AuthorizationError(f"'{sensitivity_level.value}' content requires at least '{minimum_required.value}', principal '{principal_id}' has '{role.value}'")

        from memory_platform.domain.enums import permissions_for_role
        if permission not in permissions_for_role(role):
            raise AuthorizationError(f"principal '{principal_id}' (role '{role.value}') lacks permission '{permission.value}'")
        return role
