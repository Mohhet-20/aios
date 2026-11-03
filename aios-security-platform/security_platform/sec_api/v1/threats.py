"""Threat Detection API: the nine detector checks (brute force, API
abuse, tool abuse, privilege escalation, credential abuse, suspicious
workflow, malicious prompt, anomaly, behavior deviation) and the
detected -> investigating -> confirmed/dismissed -> mitigated
lifecycle."""
from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from security_platform.dependencies.dependencies import get_current_tenant_id, get_threat_detection_service
from security_platform.sec_api.serialization import to_dict
from security_platform.threat_detection.threat_service import ThreatDetectionService

router = APIRouter(prefix="/threats", tags=["threats"])


class RateWindowCheckRequest(BaseModel):
    entity_type: str
    entity_id: str
    timestamps: list[datetime]


@router.post("/checks/brute-force", status_code=201)
async def check_brute_force(body: RateWindowCheckRequest, tenant_id: str = Depends(get_current_tenant_id), service: ThreatDetectionService = Depends(get_threat_detection_service)):
    return to_dict(await service.check_brute_force(tenant_id, body.entity_type, body.entity_id, body.timestamps))


@router.post("/checks/api-abuse", status_code=201)
async def check_api_abuse(body: RateWindowCheckRequest, tenant_id: str = Depends(get_current_tenant_id), service: ThreatDetectionService = Depends(get_threat_detection_service)):
    return to_dict(await service.check_api_abuse(tenant_id, body.entity_type, body.entity_id, body.timestamps))


@router.post("/checks/tool-abuse", status_code=201)
async def check_tool_abuse(body: RateWindowCheckRequest, tenant_id: str = Depends(get_current_tenant_id), service: ThreatDetectionService = Depends(get_threat_detection_service)):
    return to_dict(await service.check_tool_abuse(tenant_id, body.entity_type, body.entity_id, body.timestamps))


class PrivilegeEscalationRequest(BaseModel):
    entity_type: str
    entity_id: str
    previous_role_rank: int
    new_role_rank: int
    approved: bool


@router.post("/checks/privilege-escalation", status_code=201)
async def check_privilege_escalation(body: PrivilegeEscalationRequest, tenant_id: str = Depends(get_current_tenant_id), service: ThreatDetectionService = Depends(get_threat_detection_service)):
    return to_dict(
        await service.check_privilege_escalation(
            tenant_id, body.entity_type, body.entity_id, previous_role_rank=body.previous_role_rank,
            new_role_rank=body.new_role_rank, approved=body.approved,
        )
    )


class CredentialAbuseRequest(BaseModel):
    entity_type: str
    entity_id: str
    distinct_source_count: int


@router.post("/checks/credential-abuse", status_code=201)
async def check_credential_abuse(body: CredentialAbuseRequest, tenant_id: str = Depends(get_current_tenant_id), service: ThreatDetectionService = Depends(get_threat_detection_service)):
    return to_dict(await service.check_credential_abuse(tenant_id, body.entity_type, body.entity_id, distinct_source_count=body.distinct_source_count))


class SuspiciousWorkflowRequest(BaseModel):
    entity_type: str
    entity_id: str
    step_count: int
    external_call_count: int


@router.post("/checks/suspicious-workflow", status_code=201)
async def check_suspicious_workflow(body: SuspiciousWorkflowRequest, tenant_id: str = Depends(get_current_tenant_id), service: ThreatDetectionService = Depends(get_threat_detection_service)):
    return to_dict(
        await service.check_suspicious_workflow(tenant_id, body.entity_type, body.entity_id, step_count=body.step_count, external_call_count=body.external_call_count)
    )


class MaliciousPromptRequest(BaseModel):
    entity_type: str
    entity_id: str
    text: str


@router.post("/checks/malicious-prompt", status_code=201)
async def check_malicious_prompt(body: MaliciousPromptRequest, tenant_id: str = Depends(get_current_tenant_id), service: ThreatDetectionService = Depends(get_threat_detection_service)):
    return to_dict(await service.check_malicious_prompt(tenant_id, body.entity_type, body.entity_id, body.text))


class AnomalyRequest(BaseModel):
    entity_type: str
    entity_id: str
    metric_name: str
    value: float
    baseline: list[float]
    z_threshold: float = 3.0


@router.post("/checks/anomaly", status_code=201)
async def check_anomaly(body: AnomalyRequest, tenant_id: str = Depends(get_current_tenant_id), service: ThreatDetectionService = Depends(get_threat_detection_service)):
    return to_dict(
        await service.check_anomaly(tenant_id, body.entity_type, body.entity_id, body.metric_name, body.value, body.baseline, z_threshold=body.z_threshold)
    )


class BehaviorRequest(BaseModel):
    entity_type: str
    entity_id: str
    recent_actions: list[str]
    typical_actions: list[str]


@router.post("/checks/behavior", status_code=201)
async def check_behavior(body: BehaviorRequest, tenant_id: str = Depends(get_current_tenant_id), service: ThreatDetectionService = Depends(get_threat_detection_service)):
    return to_dict(await service.check_behavior(tenant_id, body.entity_type, body.entity_id, body.recent_actions, set(body.typical_actions)))


@router.post("/{threat_id}/investigate")
async def investigate(threat_id: str, tenant_id: str = Depends(get_current_tenant_id), service: ThreatDetectionService = Depends(get_threat_detection_service)):
    return to_dict(await service.investigate(tenant_id, threat_id))


@router.post("/{threat_id}/confirm")
async def confirm(threat_id: str, tenant_id: str = Depends(get_current_tenant_id), service: ThreatDetectionService = Depends(get_threat_detection_service)):
    return to_dict(await service.confirm(tenant_id, threat_id))


class ResolveThreatRequest(BaseModel):
    resolution_notes: str | None = None


@router.post("/{threat_id}/dismiss")
async def dismiss(threat_id: str, body: ResolveThreatRequest, tenant_id: str = Depends(get_current_tenant_id), service: ThreatDetectionService = Depends(get_threat_detection_service)):
    return to_dict(await service.dismiss(tenant_id, threat_id, resolution_notes=body.resolution_notes))


@router.post("/{threat_id}/mitigate")
async def mitigate(threat_id: str, body: ResolveThreatRequest, tenant_id: str = Depends(get_current_tenant_id), service: ThreatDetectionService = Depends(get_threat_detection_service)):
    return to_dict(await service.mitigate(tenant_id, threat_id, resolution_notes=body.resolution_notes))
