"""Multi-tenancy: quota usage and tier changes."""
from __future__ import annotations

from dataclasses import asdict

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from identity_platform.dependencies.dependencies import get_tenant_tier_service, get_tenant_usage_service
from identity_platform.domain.enums import TenantTier
from identity_platform.identity_api.serialization import to_dict
from identity_platform.tenancy.tier_service import TenantTierService
from identity_platform.tenancy.usage_service import TenantUsageService

router = APIRouter(prefix="/tenancy", tags=["tenancy"])


@router.get("/organizations/{organization_id}/usage")
async def get_usage(organization_id: str, service: TenantUsageService = Depends(get_tenant_usage_service)):
    usage = await service.get_usage(organization_id)
    return {
        **asdict(usage), "seat_utilization": usage.seat_utilization, "workspace_utilization": usage.workspace_utilization,
        "is_over_seat_quota": usage.is_over_seat_quota, "is_over_workspace_quota": usage.is_over_workspace_quota,
    }


class ChangeTierRequest(BaseModel):
    new_tier: TenantTier
    force: bool = False


@router.post("/organizations/{organization_id}/tier")
async def change_tier(organization_id: str, body: ChangeTierRequest, service: TenantTierService = Depends(get_tenant_tier_service)):
    return to_dict(await service.change_tier(organization_id, body.new_tier, force=body.force))
