"""AI Quality / Evaluation Regression Engine: baselines, evaluation
recording, and regression scans."""
from __future__ import annotations

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from quality_platform.ai_quality.baseline_service import BaselineService
from quality_platform.ai_quality.evaluation_service import EvaluationService
from quality_platform.ai_quality.regression_scan_service import RegressionScanService
from quality_platform.dependencies.dependencies import (
    get_baseline_service,
    get_current_tenant_id,
    get_evaluation_service,
    get_regression_scan_service,
)
from quality_platform.qa_api.serialization import to_dict, to_dict_list

router = APIRouter(prefix="/ai-quality", tags=["ai-quality"])


class SetBaselineRequest(BaseModel):
    dimension: str
    subject_ref: str
    baseline_score: float
    sample_size: int


@router.post("/baselines", status_code=201)
async def set_baseline(
    body: SetBaselineRequest, tenant_id: str = Depends(get_current_tenant_id), service: BaselineService = Depends(get_baseline_service),
):
    return to_dict(await service.set_baseline(tenant_id, body.dimension, body.subject_ref, baseline_score=body.baseline_score, sample_size=body.sample_size))


@router.get("/baselines/{dimension}/{subject_ref}")
async def get_baseline(
    dimension: str, subject_ref: str, tenant_id: str = Depends(get_current_tenant_id), service: BaselineService = Depends(get_baseline_service),
):
    return to_dict(await service.get_baseline_or_404(tenant_id, dimension, subject_ref))


class RecordEvaluationRequest(BaseModel):
    dimension: str
    subject_ref: str
    score: float


@router.post("/evaluations", status_code=201)
async def record_evaluation(
    body: RecordEvaluationRequest, tenant_id: str = Depends(get_current_tenant_id), service: EvaluationService = Depends(get_evaluation_service),
):
    return to_dict(await service.record_evaluation(tenant_id, body.dimension, body.subject_ref, score=body.score))


@router.get("/evaluations/{dimension}/{subject_ref}")
async def list_evaluations(
    dimension: str, subject_ref: str, tenant_id: str = Depends(get_current_tenant_id), service: EvaluationService = Depends(get_evaluation_service),
):
    return to_dict_list(await service.list_for_subject(tenant_id, dimension, subject_ref))


class RequestScanRequest(BaseModel):
    dimension: str
    subject_ref: str


@router.post("/regression-scans", status_code=201)
async def request_scan(
    body: RequestScanRequest, tenant_id: str = Depends(get_current_tenant_id), service: RegressionScanService = Depends(get_regression_scan_service),
):
    return to_dict(await service.request_scan(tenant_id, body.dimension, body.subject_ref))


@router.post("/regression-scans/{scan_id}/run")
async def run_scan(
    scan_id: str, tenant_id: str = Depends(get_current_tenant_id), service: RegressionScanService = Depends(get_regression_scan_service),
):
    return to_dict(await service.run_scan(tenant_id, scan_id))


@router.get("/regression-scans/{scan_id}")
async def get_scan(
    scan_id: str, tenant_id: str = Depends(get_current_tenant_id), service: RegressionScanService = Depends(get_regression_scan_service),
):
    return to_dict(await service.get_or_404(tenant_id, scan_id))


@router.get("/regression-scans")
async def list_scans(
    dimension: str | None = None, tenant_id: str = Depends(get_current_tenant_id), service: RegressionScanService = Depends(get_regression_scan_service),
):
    return to_dict_list(await service.list_scans(tenant_id, dimension=dimension))
