"""Tests for Multi-Cloud: account registration (provider validation +
dedup), activation toggling, and resource tracking gated on an active
account."""
from __future__ import annotations

import pytest

from infra_platform.cloud.cloud_service import CloudAccountService, CloudResourceService
from infra_platform.core.exceptions import CloudError, CloudResourceError, NotFoundError, UnsupportedProviderError

TENANT = "tenant-cloud"


@pytest.mark.asyncio
async def test_register_account_rejects_unknown_provider(repos):
    service = CloudAccountService(repos)
    with pytest.raises(UnsupportedProviderError):
        await service.register_account(TENANT, provider="oracle_cloud", account_ref="acct-1", display_name="Oracle")


@pytest.mark.asyncio
async def test_register_account_rejects_duplicate_ref(repos):
    service = CloudAccountService(repos)
    await service.register_account(TENANT, provider="aws", account_ref="123456789", display_name="Prod AWS")
    with pytest.raises(CloudError):
        await service.register_account(TENANT, provider="aws", account_ref="123456789", display_name="Prod AWS Dup")


@pytest.mark.asyncio
async def test_deactivate_and_reactivate_account(repos):
    service = CloudAccountService(repos)
    account = await service.register_account(TENANT, provider="gcp", account_ref="proj-1", display_name="GCP Project")
    account = await service.deactivate(TENANT, account.id)
    assert account.is_active is False
    account = await service.reactivate(TENANT, account.id)
    assert account.is_active is True


@pytest.mark.asyncio
async def test_track_resource_requires_active_account(repos):
    account_service = CloudAccountService(repos)
    resource_service = CloudResourceService(repos)
    account = await account_service.register_account(TENANT, provider="azure", account_ref="sub-1", display_name="Azure Sub")
    await account_service.deactivate(TENANT, account.id)

    with pytest.raises(CloudError):
        await resource_service.track_resource(TENANT, account.id, region="eastus", resource_type="vm", external_id="vm-1")

    await account_service.reactivate(TENANT, account.id)
    resource = await resource_service.track_resource(TENANT, account.id, region="eastus", resource_type="vm", external_id="vm-1")
    assert resource.status == "active"
    assert resource.provider == "azure"


@pytest.mark.asyncio
async def test_update_resource_status_and_unknown_resource(repos):
    account_service = CloudAccountService(repos)
    resource_service = CloudResourceService(repos)
    account = await account_service.register_account(TENANT, provider="aws", account_ref="acct-2", display_name="AWS 2")
    resource = await resource_service.track_resource(TENANT, account.id, region="us-west-2", resource_type="s3_bucket", external_id="bucket-1")

    resource = await resource_service.update_status(TENANT, resource.id, status="terminated")
    assert resource.status == "terminated"

    with pytest.raises(CloudResourceError):
        await resource_service.update_status(TENANT, "no-such-resource", status="active")


@pytest.mark.asyncio
async def test_track_resource_unknown_account_raises(repos):
    resource_service = CloudResourceService(repos)
    with pytest.raises(NotFoundError):
        await resource_service.track_resource(TENANT, "no-such-account", region="us-east-1", resource_type="vm", external_id="x")
