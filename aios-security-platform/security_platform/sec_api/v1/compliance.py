"""Compliance API: framework configuration, evidence collection,
retention policies, legal holds, consent tracking, and data
residency."""
from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from security_platform.compliance.compliance_service import ComplianceService
from security_platform.dependencies.dependencies import get_compliance_service, get_current_tenant_id
from security_platform.sec_api.serialization import to_dict, to_dict_list

router = APIRouter(prefix="/compliance", tags=["compliance"])


class EnableFrameworkRequest(BaseModel):
    framework: str
    notes: str | None = None


@router.post("/frameworks", status_code=201)
async def enable_framework(body: EnableFrameworkRequest, tenant_id: str = Depends(get_current_tenant_id), service: ComplianceService = Depends(get_compliance_service)):
    return to_dict(await service.enable_framework(tenant_id, body.framework, notes=body.notes))


@router.post("/frameworks/{framework}/disable")
async def disable_framework(framework: str, tenant_id: str = Depends(get_current_tenant_id), service: ComplianceService = Depends(get_compliance_service)):
    return to_dict(await service.disable_framework(tenant_id, framework))


@router.get("/frameworks")
async def list_enabled_frameworks(tenant_id: str = Depends(get_current_tenant_id), service: ComplianceService = Depends(get_compliance_service)):
    return to_dict_list(await service.list_enabled_frameworks(tenant_id))


class CollectEvidenceRequest(BaseModel):
    framework: str
    control_id: str
    evidence_type: str
    description: str
    resource_ref: str | None = None


@router.post("/evidence", status_code=201)
async def collect_evidence(body: CollectEvidenceRequest, tenant_id: str = Depends(get_current_tenant_id), service: ComplianceService = Depends(get_compliance_service)):
    return to_dict(await service.collect_evidence(tenant_id, **body.model_dump()))


@router.get("/evidence")
async def evidence_for_framework(framework: str, limit: int = 500, tenant_id: str = Depends(get_current_tenant_id), service: ComplianceService = Depends(get_compliance_service)):
    return to_dict_list(await service.evidence_for_framework(tenant_id, framework, limit=limit))


class SetRetentionPolicyRequest(BaseModel):
    resource_type: str
    retention_days: int
    is_enabled: bool = True


@router.put("/retention-policies")
async def set_retention_policy(body: SetRetentionPolicyRequest, tenant_id: str = Depends(get_current_tenant_id), service: ComplianceService = Depends(get_compliance_service)):
    return to_dict(await service.set_retention_policy(tenant_id, body.resource_type, body.retention_days, is_enabled=body.is_enabled))


class OpenLegalHoldRequest(BaseModel):
    name: str
    reason: str
    resource_type: str | None = None
    resource_id: str | None = None


@router.post("/legal-holds", status_code=201)
async def open_legal_hold(body: OpenLegalHoldRequest, tenant_id: str = Depends(get_current_tenant_id), service: ComplianceService = Depends(get_compliance_service)):
    return to_dict(await service.open_legal_hold(tenant_id, body.name, body.reason, resource_type=body.resource_type, resource_id=body.resource_id))


@router.post("/legal-holds/{hold_id}/release")
async def release_legal_hold(hold_id: str, tenant_id: str = Depends(get_current_tenant_id), service: ComplianceService = Depends(get_compliance_service)):
    return to_dict(await service.release_legal_hold(tenant_id, hold_id))


@router.get("/deletion-allowed/{resource_type}/{resource_id}")
async def check_deletion_allowed(resource_type: str, resource_id: str, tenant_id: str = Depends(get_current_tenant_id), service: ComplianceService = Depends(get_compliance_service)):
    return {"allowed": await service.check_deletion_allowed(tenant_id, resource_type, resource_id)}


class ConsentRequest(BaseModel):
    subject_id: str
    purpose: str
    expires_at: datetime | None = None


@router.post("/consent", status_code=201)
async def record_consent(body: ConsentRequest, tenant_id: str = Depends(get_current_tenant_id), service: ComplianceService = Depends(get_compliance_service)):
    return to_dict(await service.record_consent(tenant_id, body.subject_id, body.purpose, expires_at=body.expires_at))


@router.post("/consent/withdraw")
async def withdraw_consent(subject_id: str, purpose: str, tenant_id: str = Depends(get_current_tenant_id), service: ComplianceService = Depends(get_compliance_service)):
    return to_dict(await service.withdraw_consent(tenant_id, subject_id, purpose))


@router.get("/consent/active")
async def is_consent_active(subject_id: str, purpose: str, tenant_id: str = Depends(get_current_tenant_id), service: ComplianceService = Depends(get_compliance_service)):
    return {"active": await service.is_consent_active(tenant_id, subject_id, purpose)}


class RecordResidencyRequest(BaseModel):
    resource_type: str
    resource_id: str
    region: str


@router.put("/data-residency")
async def record_residency(body: RecordResidencyRequest, tenant_id: str = Depends(get_current_tenant_id), service: ComplianceService = Depends(get_compliance_service)):
    return to_dict(await service.record_residency(tenant_id, body.resource_type, body.resource_id, body.region))


@router.get("/data-residency/allowed/{resource_type}/{resource_id}")
async def check_residency_allowed(resource_type: str, resource_id: str, allowed_regions: str, tenant_id: str = Depends(get_current_tenant_id), service: ComplianceService = Depends(get_compliance_service)):
    return {"allowed": await service.check_residency_allowed(tenant_id, resource_type, resource_id, allowed_regions.split(","))}
