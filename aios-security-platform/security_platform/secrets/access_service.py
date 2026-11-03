"""Secret access policy management: who (principal) may read or
rotate which secret, optionally time-boxed. Kept separate from
SecretService so granting/revoking access — an administrative act — is
a distinct, independently testable surface from the vault operations
themselves."""
from __future__ import annotations

from security_platform.models.secrets import SecretAccessPolicyModel
from security_platform.repositories.registry import RepositoryRegistry


class SecretAccessService:
    def __init__(self, repos: RepositoryRegistry):
        self.repos = repos

    async def grant_access(
        self, tenant_id: str, secret_id: str, principal_id: str, *,
        can_read: bool = True, can_rotate: bool = False, expires_at=None,
    ) -> SecretAccessPolicyModel:
        existing = await self.repos.secret_access_policies.get_for_principal(tenant_id, secret_id, principal_id)
        if existing is not None:
            existing.can_read = can_read
            existing.can_rotate = can_rotate
            existing.expires_at = expires_at
            return await self.repos.secret_access_policies.update(existing)
        policy = SecretAccessPolicyModel(
            tenant_id=tenant_id, secret_id=secret_id, principal_id=principal_id,
            can_read=can_read, can_rotate=can_rotate, expires_at=expires_at,
        )
        return await self.repos.secret_access_policies.add(policy)

    async def revoke_access(self, tenant_id: str, secret_id: str, principal_id: str) -> None:
        existing = await self.repos.secret_access_policies.get_for_principal(tenant_id, secret_id, principal_id)
        if existing is not None:
            await self.repos.secret_access_policies.delete(existing)
