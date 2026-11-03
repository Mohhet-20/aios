"""Feature Flag Platform: flags, targeted overrides, and evaluation."""
from __future__ import annotations

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from release_platform.dependencies.dependencies import (
    get_current_tenant_id,
    get_feature_flag_override_service,
    get_feature_flag_service,
)
from release_platform.feature_flags.feature_flag_service import FeatureFlagOverrideService, FeatureFlagService
from release_platform.release_api.serialization import to_dict, to_dict_list

router = APIRouter(prefix="/feature-flags", tags=["feature-flags"])
overrides_router = APIRouter(prefix="/feature-flag-overrides", tags=["feature-flags"])


class CreateFlagRequest(BaseModel):
    key: str
    name: str
    scope: str = "global"
    enabled: bool = False
    rollout_pct: float = 0.0
    description: str = ""


@router.post("", status_code=201)
async def create_flag(
    body: CreateFlagRequest, tenant_id: str = Depends(get_current_tenant_id), service: FeatureFlagService = Depends(get_feature_flag_service),
):
    return to_dict(await service.create_flag(tenant_id, **body.model_dump()))


@router.get("")
async def list_flags(
    scope: str | None = None, tenant_id: str = Depends(get_current_tenant_id), service: FeatureFlagService = Depends(get_feature_flag_service),
):
    return to_dict_list(await service.list_flags(tenant_id, scope=scope))


@router.get("/{flag_id}")
async def get_flag(
    flag_id: str, tenant_id: str = Depends(get_current_tenant_id), service: FeatureFlagService = Depends(get_feature_flag_service),
):
    return to_dict(await service.get_or_404(tenant_id, flag_id))


@router.post("/{flag_id}/enable")
async def enable_flag(
    flag_id: str, tenant_id: str = Depends(get_current_tenant_id), service: FeatureFlagService = Depends(get_feature_flag_service),
):
    return to_dict(await service.enable(tenant_id, flag_id))


@router.post("/{flag_id}/disable")
async def disable_flag(
    flag_id: str, tenant_id: str = Depends(get_current_tenant_id), service: FeatureFlagService = Depends(get_feature_flag_service),
):
    return to_dict(await service.disable(tenant_id, flag_id))


@router.post("/{flag_id}/emergency-disable")
async def emergency_disable_flag(
    flag_id: str, tenant_id: str = Depends(get_current_tenant_id), service: FeatureFlagService = Depends(get_feature_flag_service),
):
    return to_dict(await service.emergency_disable(tenant_id, flag_id))


class SetRolloutPctRequest(BaseModel):
    rollout_pct: float


@router.put("/{flag_id}/rollout-pct")
async def set_rollout_pct(
    flag_id: str, body: SetRolloutPctRequest,
    tenant_id: str = Depends(get_current_tenant_id), service: FeatureFlagService = Depends(get_feature_flag_service),
):
    return to_dict(await service.set_rollout_pct(tenant_id, flag_id, rollout_pct=body.rollout_pct))


class SetOverrideRequest(BaseModel):
    flag_id: str
    target_ref: str
    enabled: bool
    config_overrides: dict | None = None


@overrides_router.post("", status_code=201)
async def set_override(
    body: SetOverrideRequest, tenant_id: str = Depends(get_current_tenant_id), service: FeatureFlagOverrideService = Depends(get_feature_flag_override_service),
):
    return to_dict(await service.set_override(tenant_id, **body.model_dump()))


@overrides_router.get("/by-flag/{flag_id}")
async def list_overrides(
    flag_id: str, tenant_id: str = Depends(get_current_tenant_id), service: FeatureFlagOverrideService = Depends(get_feature_flag_override_service),
):
    return to_dict_list(await service.list_overrides(tenant_id, flag_id))


@overrides_router.get("/{flag_id}/evaluate/{target_ref}")
async def is_enabled_for(
    flag_id: str, target_ref: str, tenant_id: str = Depends(get_current_tenant_id), service: FeatureFlagOverrideService = Depends(get_feature_flag_override_service),
):
    enabled = await service.is_enabled_for(tenant_id, flag_id, target_ref)
    return {"flag_id": flag_id, "target_ref": target_ref, "enabled": enabled}
