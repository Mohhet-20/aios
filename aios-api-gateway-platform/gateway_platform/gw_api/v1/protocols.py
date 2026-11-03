"""Protocol Translation: config registry + request/response translation."""
from __future__ import annotations

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from gateway_platform.dependencies.dependencies import (
    get_current_tenant_id,
    get_protocol_translation_config_service,
    get_protocol_translation_service,
)
from gateway_platform.gw_api.serialization import to_dict, to_dict_list
from gateway_platform.protocols.config_service import ProtocolTranslationConfigService
from gateway_platform.protocols.translation_service import ProtocolTranslationService

router = APIRouter(prefix="/protocol-translations", tags=["protocol-translation"])


class RegisterConfigRequest(BaseModel):
    route_id: str
    translation_pair: str
    config: dict | None = None


@router.post("", status_code=201)
async def register_translation_config(
    body: RegisterConfigRequest, tenant_id: str = Depends(get_current_tenant_id), service: ProtocolTranslationConfigService = Depends(get_protocol_translation_config_service),
):
    payload = body.model_dump()
    route_id = payload.pop("route_id")
    return to_dict(await service.register_config(tenant_id, route_id, **payload))


@router.get("/for-route/{route_id}")
async def list_translation_configs(
    route_id: str, tenant_id: str = Depends(get_current_tenant_id), service: ProtocolTranslationConfigService = Depends(get_protocol_translation_config_service),
):
    return to_dict_list(await service.list_for_route(tenant_id, route_id))


@router.post("/{config_id}/activate")
async def activate_translation_config(
    config_id: str, tenant_id: str = Depends(get_current_tenant_id), service: ProtocolTranslationConfigService = Depends(get_protocol_translation_config_service),
):
    return to_dict(await service.activate_config(tenant_id, config_id))


@router.post("/{config_id}/deactivate")
async def deactivate_translation_config(
    config_id: str, tenant_id: str = Depends(get_current_tenant_id), service: ProtocolTranslationConfigService = Depends(get_protocol_translation_config_service),
):
    return to_dict(await service.deactivate_config(tenant_id, config_id))


class TranslateRequest(BaseModel):
    route_id: str
    translation_pair: str
    payload: dict


@router.post("/translate-request")
async def translate_request(
    body: TranslateRequest, tenant_id: str = Depends(get_current_tenant_id), service: ProtocolTranslationService = Depends(get_protocol_translation_service),
):
    return await service.translate_request(tenant_id, body.route_id, translation_pair=body.translation_pair, payload=body.payload)


@router.post("/translate-response")
async def translate_response(
    body: TranslateRequest, tenant_id: str = Depends(get_current_tenant_id), service: ProtocolTranslationService = Depends(get_protocol_translation_service),
):
    return await service.translate_response(tenant_id, body.route_id, translation_pair=body.translation_pair, payload=body.payload)
