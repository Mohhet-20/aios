"""Multi-cloud: cloud accounts (a credential/subscription reference
per provider — never raw credentials) and cloud resources, a generic
pointer to anything actually provisioned in a real cloud, following
the same "own the pointer, not the data" posture as the Model
Registry's artifacts and the Security Platform's governed assets.

DISCLOSED SCOPE BOUNDARY: this platform tracks which cloud resources
exist and which account they belong to; it does not itself call a
real AWS/Azure/GCP API to provision anything — that's the seam a real
cloud-provider adapter would plug in at, the same posture as the
Kubernetes module's control-plane-without-a-kubeconfig boundary."""
from __future__ import annotations

from infra_platform.core.exceptions import CloudError, CloudResourceError, NotFoundError, UnsupportedProviderError
from infra_platform.domain.enums import CloudProvider
from infra_platform.models.cloud import CloudAccountModel, CloudResourceModel
from infra_platform.repositories.registry import RepositoryRegistry

_VALID_PROVIDERS = {p.value for p in CloudProvider}


class CloudAccountService:
    def __init__(self, repos: RepositoryRegistry):
        self.repos = repos

    async def register_account(
        self, tenant_id: str, *, provider: str, account_ref: str, display_name: str
    ) -> CloudAccountModel:
        if provider not in _VALID_PROVIDERS:
            raise UnsupportedProviderError(f"Unsupported cloud provider '{provider}'")
        existing = await self.repos.cloud_accounts.list_by_provider(tenant_id, provider)
        if any(a.account_ref == account_ref for a in existing):
            raise CloudError(f"Cloud account '{account_ref}' already registered for provider '{provider}'")
        account = CloudAccountModel(tenant_id=tenant_id, provider=provider, account_ref=account_ref, display_name=display_name, is_active=True)
        return await self.repos.cloud_accounts.add(account)

    async def _get(self, tenant_id: str, account_id: str) -> CloudAccountModel:
        account = await self.repos.cloud_accounts.get(account_id)
        if account is None or account.tenant_id != tenant_id:
            raise NotFoundError(f"CloudAccount '{account_id}' not found")
        return account

    async def deactivate(self, tenant_id: str, account_id: str) -> CloudAccountModel:
        account = await self._get(tenant_id, account_id)
        account.is_active = False
        return await self.repos.cloud_accounts.update(account)

    async def reactivate(self, tenant_id: str, account_id: str) -> CloudAccountModel:
        account = await self._get(tenant_id, account_id)
        account.is_active = True
        return await self.repos.cloud_accounts.update(account)

    async def list_for_tenant(self, tenant_id: str) -> list[CloudAccountModel]:
        return await self.repos.cloud_accounts.list_for_tenant(tenant_id)

    async def list_by_provider(self, tenant_id: str, provider: str) -> list[CloudAccountModel]:
        return await self.repos.cloud_accounts.list_by_provider(tenant_id, provider)


class CloudResourceService:
    def __init__(self, repos: RepositoryRegistry):
        self.repos = repos

    async def track_resource(
        self, tenant_id: str, cloud_account_id: str, *, region: str, resource_type: str, external_id: str, tags: dict | None = None
    ) -> CloudResourceModel:
        account = await self.repos.cloud_accounts.get(cloud_account_id)
        if account is None or account.tenant_id != tenant_id:
            raise NotFoundError(f"CloudAccount '{cloud_account_id}' not found")
        if not account.is_active:
            raise CloudError(f"CloudAccount '{cloud_account_id}' is not active")
        resource = CloudResourceModel(
            tenant_id=tenant_id, cloud_account_id=cloud_account_id, provider=account.provider, region=region,
            resource_type=resource_type, external_id=external_id, status="active", tags=tags or {},
        )
        return await self.repos.cloud_resources.add(resource)

    async def _get(self, tenant_id: str, resource_id: str) -> CloudResourceModel:
        resource = await self.repos.cloud_resources.get(resource_id)
        if resource is None or resource.tenant_id != tenant_id:
            raise CloudResourceError(f"CloudResource '{resource_id}' not found")
        return resource

    async def update_status(self, tenant_id: str, resource_id: str, *, status: str) -> CloudResourceModel:
        resource = await self._get(tenant_id, resource_id)
        resource.status = status
        return await self.repos.cloud_resources.update(resource)

    async def list_for_account(self, tenant_id: str, cloud_account_id: str) -> list[CloudResourceModel]:
        return await self.repos.cloud_resources.list_for_account(tenant_id, cloud_account_id)

    async def list_by_type(self, tenant_id: str, resource_type: str) -> list[CloudResourceModel]:
        return await self.repos.cloud_resources.list_by_type(tenant_id, resource_type)
