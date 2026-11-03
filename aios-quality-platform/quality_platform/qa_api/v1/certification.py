"""Release Certification Engine: certification run lifecycle combining
category scores into an overall score and deployment decision."""
from __future__ import annotations

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from quality_platform.certification.certification_run_service import CertificationRunService
from quality_platform.dependencies.dependencies import get_certification_run_service, get_current_tenant_id
from quality_platform.qa_api.serialization import to_dict, to_dict_list

router = APIRouter(prefix="/certification-runs", tags=["certification"])


class RequestRunRequest(BaseModel):
    release_ref: str


@router.post("", status_code=201)
async def request_run(
    body: RequestRunRequest, tenant_id: str = Depends(get_current_tenant_id), service: CertificationRunService = Depends(get_certification_run_service),
):
    return to_dict(await service.request_run(tenant_id, release_ref=body.release_ref))


@router.get("/{run_id}")
async def get_run(
    run_id: str, tenant_id: str = Depends(get_current_tenant_id), service: CertificationRunService = Depends(get_certification_run_service),
):
    return to_dict(await service.get_or_404(tenant_id, run_id))


class CertifyRequest(BaseModel):
    quality_score: float | None = None
    reliability_score: float | None = None
    security_score: float | None = None
    performance_score: float | None = None
    ai_quality_score: float | None = None


@router.post("/{run_id}/certify")
async def certify(
    run_id: str, body: CertifyRequest, tenant_id: str = Depends(get_current_tenant_id), service: CertificationRunService = Depends(get_certification_run_service),
):
    return to_dict(await service.certify(tenant_id, run_id, **body.model_dump()))


@router.get("")
async def list_for_release(
    release_ref: str, tenant_id: str = Depends(get_current_tenant_id), service: CertificationRunService = Depends(get_certification_run_service),
):
    return to_dict_list(await service.list_for_release(tenant_id, release_ref))
