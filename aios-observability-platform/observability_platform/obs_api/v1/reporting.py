"""Reporting API."""
from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from observability_platform.dependencies.dependencies import get_current_actor_id, get_current_tenant_id, get_report_service, get_repos
from observability_platform.obs_api.serialization import to_dict, to_dict_list
from observability_platform.repositories.registry import RepositoryRegistry
from observability_platform.reporting.report_service import ReportService

router = APIRouter(prefix="/reports", tags=["reports"])


class GenerateReportRequest(BaseModel):
    report_type: str
    title: str | None = None
    period_start: datetime | None = None
    period_end: datetime | None = None
    params: dict | None = None


@router.post("/generate", status_code=201)
async def generate_report(
    body: GenerateReportRequest, tenant_id: str = Depends(get_current_tenant_id), actor_id: str | None = Depends(get_current_actor_id),
    service: ReportService = Depends(get_report_service),
):
    return to_dict(await service.generate_report(tenant_id, generated_by=actor_id, **body.model_dump()))


@router.get("")
async def list_reports(tenant_id: str = Depends(get_current_tenant_id), report_type: str | None = None, repos: RepositoryRegistry = Depends(get_repos)):
    return to_dict_list(await repos.reports.list_for_tenant(tenant_id, report_type=report_type))
