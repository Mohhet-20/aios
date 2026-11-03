"""Reporting Platform: report definitions and their generation runs."""
from __future__ import annotations

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from analytics_platform.an_api.serialization import to_dict, to_dict_list
from analytics_platform.dependencies.dependencies import (
    get_current_tenant_id,
    get_report_definition_service,
    get_report_run_service,
)
from analytics_platform.reports.report_definition_service import ReportDefinitionService
from analytics_platform.reports.report_run_service import ReportRunService

router = APIRouter(prefix="/report-definitions", tags=["reports"])
runs_router = APIRouter(prefix="/report-runs", tags=["reports"])


class RegisterReportRequest(BaseModel):
    name: str
    report_type: str
    report_format: str = "json"
    schedule: str = "none"
    config: dict | None = None


@router.post("", status_code=201)
async def register_report(
    body: RegisterReportRequest, tenant_id: str = Depends(get_current_tenant_id),
    service: ReportDefinitionService = Depends(get_report_definition_service),
):
    return to_dict(await service.register_report(tenant_id, **body.model_dump()))


@router.get("")
async def list_reports(
    report_type: str | None = None, tenant_id: str = Depends(get_current_tenant_id),
    service: ReportDefinitionService = Depends(get_report_definition_service),
):
    return to_dict_list(await service.list_for_tenant(tenant_id, report_type=report_type))


@router.get("/scheduled")
async def list_scheduled_reports(
    tenant_id: str = Depends(get_current_tenant_id), service: ReportDefinitionService = Depends(get_report_definition_service),
):
    return to_dict_list(await service.list_scheduled(tenant_id))


@router.get("/{definition_id}")
async def get_report(
    definition_id: str, tenant_id: str = Depends(get_current_tenant_id),
    service: ReportDefinitionService = Depends(get_report_definition_service),
):
    return to_dict(await service.get_or_404(tenant_id, definition_id))


@router.post("/{definition_id}/activate")
async def activate_report(
    definition_id: str, tenant_id: str = Depends(get_current_tenant_id),
    service: ReportDefinitionService = Depends(get_report_definition_service),
):
    return to_dict(await service.activate(tenant_id, definition_id))


@router.post("/{definition_id}/deactivate")
async def deactivate_report(
    definition_id: str, tenant_id: str = Depends(get_current_tenant_id),
    service: ReportDefinitionService = Depends(get_report_definition_service),
):
    return to_dict(await service.deactivate(tenant_id, definition_id))


@router.post("/{definition_id}/runs", status_code=201)
async def request_run(
    definition_id: str, tenant_id: str = Depends(get_current_tenant_id),
    service: ReportRunService = Depends(get_report_run_service),
):
    return to_dict(await service.request_run(tenant_id, definition_id))


@router.get("/{definition_id}/runs")
async def list_runs(
    definition_id: str, tenant_id: str = Depends(get_current_tenant_id),
    service: ReportRunService = Depends(get_report_run_service),
):
    return to_dict_list(await service.list_for_definition(tenant_id, definition_id))


@runs_router.post("/{run_id}/generate")
async def generate_run(
    run_id: str, tenant_id: str = Depends(get_current_tenant_id), service: ReportRunService = Depends(get_report_run_service),
):
    return to_dict(await service.generate(tenant_id, run_id))


@runs_router.get("/{run_id}")
async def get_run(
    run_id: str, tenant_id: str = Depends(get_current_tenant_id), service: ReportRunService = Depends(get_report_run_service),
):
    return to_dict(await service.get_or_404(tenant_id, run_id))
