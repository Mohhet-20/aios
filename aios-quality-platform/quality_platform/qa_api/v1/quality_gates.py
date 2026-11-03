"""Quality Gates & Coverage Platform: release gate lifecycle, check
recording, and coverage snapshots across the nine coverage types."""
from __future__ import annotations

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from quality_platform.dependencies.dependencies import get_coverage_service, get_current_tenant_id, get_quality_gate_service
from quality_platform.qa_api.serialization import to_dict, to_dict_list
from quality_platform.quality_gates.coverage_service import CoverageService
from quality_platform.quality_gates.quality_gate_service import QualityGateService

router = APIRouter(prefix="/quality-gates", tags=["quality-gates"])
coverage_router = APIRouter(prefix="/coverage-snapshots", tags=["quality-gates"])


class CreateGateRequest(BaseModel):
    name: str
    release_ref: str
    min_score: float | None = None


@router.post("", status_code=201)
async def create_gate(
    body: CreateGateRequest, tenant_id: str = Depends(get_current_tenant_id), service: QualityGateService = Depends(get_quality_gate_service),
):
    return to_dict(await service.create_gate(tenant_id, **body.model_dump()))


@router.get("")
async def list_gates(
    release_ref: str | None = None, tenant_id: str = Depends(get_current_tenant_id), service: QualityGateService = Depends(get_quality_gate_service),
):
    return to_dict_list(await service.list_gates(tenant_id, release_ref=release_ref))


@router.get("/{gate_id}")
async def get_gate(
    gate_id: str, tenant_id: str = Depends(get_current_tenant_id), service: QualityGateService = Depends(get_quality_gate_service),
):
    return to_dict(await service.get_or_404(tenant_id, gate_id))


class RecordCheckRequest(BaseModel):
    check_type: str
    passed: bool
    details: dict | None = None


@router.post("/{gate_id}/checks", status_code=201)
async def record_check(
    gate_id: str, body: RecordCheckRequest, tenant_id: str = Depends(get_current_tenant_id), service: QualityGateService = Depends(get_quality_gate_service),
):
    return to_dict(await service.record_check(tenant_id, gate_id, check_type=body.check_type, passed=body.passed, details=body.details))


@router.get("/{gate_id}/checks")
async def list_checks(
    gate_id: str, tenant_id: str = Depends(get_current_tenant_id), service: QualityGateService = Depends(get_quality_gate_service),
):
    return to_dict_list(await service.list_checks(tenant_id, gate_id))


@router.post("/{gate_id}/evaluate")
async def evaluate_gate(
    gate_id: str, tenant_id: str = Depends(get_current_tenant_id), service: QualityGateService = Depends(get_quality_gate_service),
):
    return to_dict(await service.evaluate_gate(tenant_id, gate_id))


@router.post("/{gate_id}/waive")
async def waive_gate(
    gate_id: str, tenant_id: str = Depends(get_current_tenant_id), service: QualityGateService = Depends(get_quality_gate_service),
):
    return to_dict(await service.waive_gate(tenant_id, gate_id))


class RecordCoverageRequest(BaseModel):
    subject_ref: str
    coverage_type: str
    covered_pct: float


@coverage_router.post("", status_code=201)
async def record_coverage(
    body: RecordCoverageRequest, tenant_id: str = Depends(get_current_tenant_id), service: CoverageService = Depends(get_coverage_service),
):
    return to_dict(await service.record_snapshot(tenant_id, body.subject_ref, coverage_type=body.coverage_type, covered_pct=body.covered_pct))


@coverage_router.get("")
async def list_coverage(
    subject_ref: str, coverage_type: str | None = None, tenant_id: str = Depends(get_current_tenant_id), service: CoverageService = Depends(get_coverage_service),
):
    return to_dict_list(await service.list_for_subject(tenant_id, subject_ref, coverage_type=coverage_type))
