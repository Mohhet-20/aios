"""Failure Analysis & Risk Analysis: recurring failure pattern
tracking and risk assessment scoring."""
from __future__ import annotations

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from quality_platform.dependencies.dependencies import get_current_tenant_id, get_failure_pattern_service, get_risk_assessment_service
from quality_platform.failure_analysis.failure_pattern_service import FailurePatternService
from quality_platform.failure_analysis.risk_assessment_service import RiskAssessmentService
from quality_platform.qa_api.serialization import to_dict, to_dict_list

router = APIRouter(prefix="/failure-patterns", tags=["failure-analysis"])
risk_router = APIRouter(prefix="/risk-assessments", tags=["failure-analysis"])


class RecordOccurrenceRequest(BaseModel):
    pattern_type: str
    subject_ref: str
    details: dict | None = None


@router.post("", status_code=201)
async def record_occurrence(
    body: RecordOccurrenceRequest, tenant_id: str = Depends(get_current_tenant_id), service: FailurePatternService = Depends(get_failure_pattern_service),
):
    return to_dict(await service.record_occurrence(tenant_id, pattern_type=body.pattern_type, subject_ref=body.subject_ref, details=body.details))


@router.get("")
async def list_patterns(
    pattern_type: str | None = None, min_occurrences: int = 1, tenant_id: str = Depends(get_current_tenant_id), service: FailurePatternService = Depends(get_failure_pattern_service),
):
    return to_dict_list(await service.list_patterns(tenant_id, pattern_type=pattern_type, min_occurrences=min_occurrences))


class AssessRiskRequest(BaseModel):
    subject_ref: str
    factors: dict[str, float]


@risk_router.post("", status_code=201)
async def assess_risk(
    body: AssessRiskRequest, tenant_id: str = Depends(get_current_tenant_id), service: RiskAssessmentService = Depends(get_risk_assessment_service),
):
    return to_dict(await service.assess(tenant_id, body.subject_ref, factors=body.factors))


@risk_router.get("")
async def list_risk_history(
    subject_ref: str, tenant_id: str = Depends(get_current_tenant_id), service: RiskAssessmentService = Depends(get_risk_assessment_service),
):
    return to_dict_list(await service.list_history(tenant_id, subject_ref))
