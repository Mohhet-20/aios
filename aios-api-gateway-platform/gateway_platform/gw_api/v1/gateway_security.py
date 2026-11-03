"""Gateway Security: policies, IP/geo filtering, request signing,
threat detection, security events."""
from __future__ import annotations

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from gateway_platform.dependencies.dependencies import (
    get_current_tenant_id,
    get_geo_filter_service,
    get_ip_filter_service,
    get_request_signing_service,
    get_security_event_service,
    get_security_policy_service,
    get_threat_detection_service,
)
from gateway_platform.gateway_security.geo_filter_service import GeoFilterService
from gateway_platform.gateway_security.ip_filter_service import IpFilterService
from gateway_platform.gateway_security.policy_service import SecurityPolicyService
from gateway_platform.gateway_security.request_signing_service import RequestSigningService
from gateway_platform.gateway_security.security_event_service import SecurityEventService
from gateway_platform.gateway_security.threat_detection_service import ThreatDetectionService
from gateway_platform.gw_api.serialization import to_dict, to_dict_list

router = APIRouter(prefix="/security/policies", tags=["gateway-security"])


class RegisterPolicyRequest(BaseModel):
    name: str
    policy_type: str
    rules: dict | None = None


@router.post("", status_code=201)
async def register_policy(
    body: RegisterPolicyRequest, tenant_id: str = Depends(get_current_tenant_id), service: SecurityPolicyService = Depends(get_security_policy_service),
):
    return to_dict(await service.register_policy(tenant_id, **body.model_dump()))


@router.get("")
async def list_policies(
    policy_type: str | None = None, tenant_id: str = Depends(get_current_tenant_id), service: SecurityPolicyService = Depends(get_security_policy_service),
):
    return to_dict_list(await service.list_for_tenant(tenant_id, policy_type=policy_type))


@router.post("/{policy_id}/activate")
async def activate_policy(
    policy_id: str, tenant_id: str = Depends(get_current_tenant_id), service: SecurityPolicyService = Depends(get_security_policy_service),
):
    return to_dict(await service.activate_policy(tenant_id, policy_id))


@router.post("/{policy_id}/deactivate")
async def deactivate_policy(
    policy_id: str, tenant_id: str = Depends(get_current_tenant_id), service: SecurityPolicyService = Depends(get_security_policy_service),
):
    return to_dict(await service.deactivate_policy(tenant_id, policy_id))


ip_filter_router = APIRouter(prefix="/security/ip-rules", tags=["gateway-security"])


class AddIpRuleRequest(BaseModel):
    policy_id: str
    cidr: str
    action: str = "deny"


@ip_filter_router.post("", status_code=201)
async def add_ip_rule(
    body: AddIpRuleRequest, tenant_id: str = Depends(get_current_tenant_id), service: IpFilterService = Depends(get_ip_filter_service),
):
    payload = body.model_dump()
    policy_id = payload.pop("policy_id")
    return to_dict(await service.add_rule(tenant_id, policy_id, **payload))


@ip_filter_router.get("/for-policy/{policy_id}")
async def list_ip_rules(
    policy_id: str, tenant_id: str = Depends(get_current_tenant_id), service: IpFilterService = Depends(get_ip_filter_service),
):
    return to_dict_list(await service.list_rules(tenant_id, policy_id))


class EvaluateIpRequest(BaseModel):
    policy_id: str
    ip_address: str


@ip_filter_router.post("/evaluate")
async def evaluate_ip(
    body: EvaluateIpRequest, tenant_id: str = Depends(get_current_tenant_id), service: IpFilterService = Depends(get_ip_filter_service),
):
    allowed = await service.evaluate(tenant_id, body.policy_id, body.ip_address)
    return {"allowed": allowed}


geo_filter_router = APIRouter(prefix="/security/geo-rules", tags=["gateway-security"])


class AddGeoRuleRequest(BaseModel):
    policy_id: str
    country_code: str
    action: str = "deny"


@geo_filter_router.post("", status_code=201)
async def add_geo_rule(
    body: AddGeoRuleRequest, tenant_id: str = Depends(get_current_tenant_id), service: GeoFilterService = Depends(get_geo_filter_service),
):
    payload = body.model_dump()
    policy_id = payload.pop("policy_id")
    return to_dict(await service.add_rule(tenant_id, policy_id, **payload))


class EvaluateGeoRequest(BaseModel):
    policy_id: str
    country_code: str


@geo_filter_router.post("/evaluate")
async def evaluate_geo(
    body: EvaluateGeoRequest, tenant_id: str = Depends(get_current_tenant_id), service: GeoFilterService = Depends(get_geo_filter_service),
):
    allowed = await service.evaluate(tenant_id, body.policy_id, body.country_code)
    return {"allowed": allowed}


signing_router = APIRouter(prefix="/security/request-signing", tags=["gateway-security"])


class VerifySignatureRequest(BaseModel):
    payload: str
    signature: str
    secret: str


@signing_router.post("/verify")
async def verify_request_signature(body: VerifySignatureRequest, service: RequestSigningService = Depends(get_request_signing_service)):
    service.verify(body.payload.encode(), body.signature, body.secret)
    return {"valid": True}


threat_router = APIRouter(prefix="/security/threat-detection", tags=["gateway-security"])


class ScanTextRequest(BaseModel):
    text: str


@threat_router.post("/scan")
async def scan_for_threats(body: ScanTextRequest, service: ThreatDetectionService = Depends(get_threat_detection_service)):
    return {"matches": service.scan_for_threats(body.text)}


class IsBotRequest(BaseModel):
    user_agent: str | None = None
    request_rate_per_minute: float = 0.0


@threat_router.post("/is-bot")
async def check_is_bot(body: IsBotRequest, service: ThreatDetectionService = Depends(get_threat_detection_service)):
    return {"is_bot": service.is_bot(body.user_agent, request_rate_per_minute=body.request_rate_per_minute)}


events_router = APIRouter(prefix="/security/events", tags=["gateway-security"])


class RecordSecurityEventRequest(BaseModel):
    event_type: str
    severity: str = "info"
    source_ip: str | None = None
    details: dict | None = None


@events_router.post("", status_code=201)
async def record_security_event(
    body: RecordSecurityEventRequest, tenant_id: str = Depends(get_current_tenant_id), service: SecurityEventService = Depends(get_security_event_service),
):
    return to_dict(await service.record_event(tenant_id, **body.model_dump()))


@events_router.get("")
async def list_security_events(
    severity: str | None = None, tenant_id: str = Depends(get_current_tenant_id), service: SecurityEventService = Depends(get_security_event_service),
):
    return to_dict_list(await service.list_recent(tenant_id, severity=severity))
