"""`Principal` is the authenticated identity attached to a request,
regardless of *how* it authenticated (JWT for a human user, or an API key
for a service account/machine client). Routers and services depend on this
one type rather than branching on "is this a user or a service account"
everywhere permission checks happen.
"""

from __future__ import annotations

from dataclasses import dataclass

from app.security.permissions import Permission, Role


@dataclass(frozen=True)
class Principal:
    id: str
    organization_id: str | None
    role: Role
    permissions: set[Permission]
    is_service_account: bool = False
    display_name: str = ""

    def has_permission(self, permission: Permission) -> bool:
        return permission in self.permissions

    def require_permission(self, permission: Permission) -> None:
        if not self.has_permission(permission):
            from app.core.exceptions import AuthorizationError

            raise AuthorizationError(
                f"Principal '{self.id}' lacks required permission '{permission.value}'",
                required_permission=permission.value,
            )
