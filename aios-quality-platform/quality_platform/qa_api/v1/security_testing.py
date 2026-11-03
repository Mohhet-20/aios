"""Security Testing Engine: scan lifecycle and finding recording
across the eleven security test types."""
from __future__ import annotations

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from quality_platform.dependencies.dependencies import get_current_tenant_id, get_security_scan_service
from quality_platform.qa_api.serialization import to_dict, to_dict_list
from quality_platform.security_testing.security_scan_service import SecurityScanService

router = APIRouter(prefix="/security-scans", tags=["security-testing"])


class RequestScanRequest(BaseModel):
    security_test_type: str
    target_ref: str


@router.post("", status_code=201)
async def request_scan(
    body: RequestScanRequest, tenant_id: str = Depends(get_current_tenant_id), service: SecurityScanService = Depends(get_security_scan_service),
):
    return to_dict(await service.request_scan(tenant_id, security_test_type=body.security_test_type, target_ref=body.target_ref))


@router.get("/{scan_id}")
async def get_scan(
    scan_id: str, tenant_id: str = Depends(get_current_tenant_id), service: SecurityScanService = Depends(get_security_scan_service),
):
    return to_dict(await service.get_or_404(tenant_id, scan_id))


@router.post("/{scan_id}/start")
async def start_scan(
    scan_id: str, tenant_id: str = Depends(get_current_tenant_id), service: SecurityScanService = Depends(get_security_scan_service),
):
    return to_dict(await service.start(tenant_id, scan_id))


class RecordFindingRequest(BaseModel):
    severity: str
    title: str
    description: str = ""


@router.post("/{scan_id}/findings", status_code=201)
async def record_finding(
    scan_id: str, body: RecordFindingRequest, tenant_id: str = Depends(get_current_tenant_id), service: SecurityScanService = Depends(get_security_scan_service),
):
    return to_dict(await service.record_finding(tenant_id, scan_id, severity=body.severity, title=body.title, description=body.description))


@router.get("/{scan_id}/findings")
async def list_findings(
    scan_id: str, tenant_id: str = Depends(get_current_tenant_id), service: SecurityScanService = Depends(get_security_scan_service),
):
    return to_dict_list(await service.list_findings(tenant_id, scan_id))


@router.post("/{scan_id}/finish")
async def finish_scan(
    scan_id: str, tenant_id: str = Depends(get_current_tenant_id), service: SecurityScanService = Depends(get_security_scan_service),
):
    return to_dict(await service.finish_scan(tenant_id, scan_id))


@router.get("")
async def list_scans(
    security_test_type: str | None = None, tenant_id: str = Depends(get_current_tenant_id), service: SecurityScanService = Depends(get_security_scan_service),
):
    return to_dict_list(await service.list_scans(tenant_id, security_test_type=security_test_type))
