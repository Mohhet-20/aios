"""Feature Store API: feature groups, versioned features, validation
rules, and publish/deprecate lifecycle."""
from __future__ import annotations

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from infra_platform.dependencies.dependencies import get_current_tenant_id, get_feature_group_service, get_feature_service
from infra_platform.feature_store.feature_store_service import FeatureGroupService, FeatureService
from infra_platform.infra_api.serialization import to_dict, to_dict_list

router = APIRouter(prefix="/features", tags=["feature-store"])


class CreateFeatureGroupRequest(BaseModel):
    name: str
    entity_key: str
    description: str | None = None
    online_enabled: bool = True
    offline_enabled: bool = True


@router.post("/groups", status_code=201)
async def create_feature_group(body: CreateFeatureGroupRequest, tenant_id: str = Depends(get_current_tenant_id), service: FeatureGroupService = Depends(get_feature_group_service)):
    return to_dict(await service.create_feature_group(tenant_id, **body.model_dump()))


@router.get("/groups")
async def list_feature_groups(tenant_id: str = Depends(get_current_tenant_id), service: FeatureGroupService = Depends(get_feature_group_service)):
    return to_dict_list(await service.list_for_tenant(tenant_id))


class CreateFeatureRequest(BaseModel):
    name: str
    value_type: str
    description: str | None = None


@router.post("/groups/{group_id}/features", status_code=201)
async def create_feature(group_id: str, body: CreateFeatureRequest, tenant_id: str = Depends(get_current_tenant_id), service: FeatureService = Depends(get_feature_service)):
    return to_dict(await service.create_feature(tenant_id, group_id, **body.model_dump()))


@router.get("/groups/{group_id}/features")
async def list_features(group_id: str, tenant_id: str = Depends(get_current_tenant_id), service: FeatureService = Depends(get_feature_service)):
    return to_dict_list(await service.list_for_group(tenant_id, group_id))


class NewVersionRequest(BaseModel):
    name: str
    value_type: str | None = None
    description: str | None = None


@router.post("/groups/{group_id}/features/new-version", status_code=201)
async def create_new_version(group_id: str, body: NewVersionRequest, tenant_id: str = Depends(get_current_tenant_id), service: FeatureService = Depends(get_feature_service)):
    return to_dict(await service.create_new_version(tenant_id, group_id, **body.model_dump()))


class AddRuleRequest(BaseModel):
    rule_type: str
    config: dict | None = None


@router.post("/{feature_id}/rules", status_code=201)
async def add_validation_rule(feature_id: str, body: AddRuleRequest, tenant_id: str = Depends(get_current_tenant_id), service: FeatureService = Depends(get_feature_service)):
    return to_dict(await service.add_validation_rule(tenant_id, feature_id, **body.model_dump()))


@router.get("/{feature_id}/rules")
async def list_rules(feature_id: str, tenant_id: str = Depends(get_current_tenant_id), service: FeatureService = Depends(get_feature_service)):
    return to_dict_list(await service.list_rules(tenant_id, feature_id))


@router.post("/{feature_id}/publish")
async def publish_feature(feature_id: str, tenant_id: str = Depends(get_current_tenant_id), service: FeatureService = Depends(get_feature_service)):
    return to_dict(await service.publish_feature(tenant_id, feature_id))


@router.post("/{feature_id}/deprecate")
async def deprecate_feature(feature_id: str, tenant_id: str = Depends(get_current_tenant_id), service: FeatureService = Depends(get_feature_service)):
    return to_dict(await service.deprecate_feature(tenant_id, feature_id))
