"""ServiceAccountService: machine identities that own API keys the way
a human user does — a service account has no password/MFA/session,
just a name, a status, and whatever API keys and role assignments are
granted to it (`principal_type="service_account"` in RBAC)."""
from __future__ import annotations

from identity_platform.domain.enums import ServiceAccountStatus
from identity_platform.models.api_key import ServiceAccountModel
from identity_platform.repositories.registry import RepositoryRegistry


class ServiceAccountService:
    def __init__(self, repos: RepositoryRegistry):
        self.repos = repos

    async def create(self, organization_id: str, *, name: str, description: str | None = None) -> ServiceAccountModel:
        await self.repos.organizations.get_or_404(organization_id)
        return await self.repos.service_accounts.add(ServiceAccountModel(
            organization_id=organization_id, name=name, description=description, status=ServiceAccountStatus.ACTIVE.value,
        ))

    async def disable(self, service_account_id: str) -> ServiceAccountModel:
        account = await self.repos.service_accounts.get_or_404(service_account_id)
        account.status = ServiceAccountStatus.DISABLED.value
        return await self.repos.service_accounts.update(account)

    async def enable(self, service_account_id: str) -> ServiceAccountModel:
        account = await self.repos.service_accounts.get_or_404(service_account_id)
        account.status = ServiceAccountStatus.ACTIVE.value
        return await self.repos.service_accounts.update(account)

    async def list_for_organization(self, organization_id: str) -> list[ServiceAccountModel]:
        return await self.repos.service_accounts.list_for_organization(organization_id)
