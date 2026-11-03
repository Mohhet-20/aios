"""Audit log queries, retention sweeps, and compliance operations."""
from __future__ import annotations

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from identity_platform.dependencies.dependencies import get_audit_service, get_compliance_service, get_retention_service
from identity_platform.domain.enums import AuditActorType
from identity_platform.governance.audit_service import AuditService
from identity_platform.governance.compliance_service import ComplianceService
from identity_platform.governance.retention_service import RetentionService
from identity_platform.identity_api.serialization import to_dict_list

router = APIRouter(prefix="/governance", tags=["governance"])


@router.get("/audit-log/organizations/{organization_id}")
async def list_audit_log_for_organization(organization_id: str, action: str | None = None, service: AuditService = Depends(get_audit_service)):
    return to_dict_list(await service.list_for_organization(organization_id, action=action))


@router.get("/audit-log/actors/{actor_type}/{actor_id}")
async def list_audit_log_for_actor(actor_type: AuditActorType, actor_id: str, service: AuditService = Depends(get_audit_service)):
    return to_dict_list(await service.list_for_actor(actor_type, actor_id))


@router.get("/audit-log/resources/{resource_type}/{resource_id}")
async def list_audit_log_for_resource(resource_type: str, resource_id: str, service: AuditService = Depends(get_audit_service)):
    return to_dict_list(await service.list_for_resource(resource_type, resource_id))


@router.post("/retention/run")
async def run_retention_sweep(service: RetentionService = Depends(get_retention_service)):
    return await service.run_all()


class UpdateComplianceMetadataRequest(BaseModel):
    metadata: dict


@router.put("/organizations/{organization_id}/compliance-metadata")
async def update_compliance_metadata(organization_id: str, body: UpdateComplianceMetadataRequest, service: ComplianceService = Depends(get_compliance_service)):
    return await service.update_compliance_metadata(organization_id, metadata=body.metadata)


@router.get("/users/{user_id}/data-export")
async def export_user_data(user_id: str, service: ComplianceService = Depends(get_compliance_service)):
    from dataclasses import asdict
    return asdict(await service.export_user_data(user_id))


@router.get("/organizations/{organization_id}/compliance-summary")
async def compliance_summary(organization_id: str, service: ComplianceService = Depends(get_compliance_service)):
    return await service.compliance_summary(organization_id)
