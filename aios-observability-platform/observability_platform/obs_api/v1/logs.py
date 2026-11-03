"""Centralized logging API: ingestion, search, and retention."""
from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from observability_platform.dependencies.dependencies import (
    get_current_tenant_id,
    get_log_ingest_service,
    get_log_retention_service,
    get_log_search_service,
)
from observability_platform.logs.ingest_service import LogIngestService
from observability_platform.logs.retention_service import LogRetentionService
from observability_platform.logs.search_service import LogSearchService
from observability_platform.obs_api.serialization import to_dict, to_dict_list

router = APIRouter(prefix="/logs", tags=["logs"])


class IngestLogRequest(BaseModel):
    service_name: str
    level: str
    message: str
    component_type: str | None = None
    context: dict | None = None
    tags: dict | None = None
    correlation_id: str | None = None
    trace_id: str | None = None
    span_id: str | None = None
    session_id: str | None = None
    user_id: str | None = None
    request_id: str | None = None


@router.post("", status_code=201)
async def ingest_log(
    body: IngestLogRequest, tenant_id: str = Depends(get_current_tenant_id), service: LogIngestService = Depends(get_log_ingest_service)
):
    return to_dict(await service.ingest(tenant_id, **body.model_dump()))


class IngestLogBatchRequest(BaseModel):
    entries: list[IngestLogRequest]


@router.post("/batch", status_code=201)
async def ingest_log_batch(
    body: IngestLogBatchRequest, tenant_id: str = Depends(get_current_tenant_id), service: LogIngestService = Depends(get_log_ingest_service)
):
    return to_dict_list(await service.ingest_batch(tenant_id, [e.model_dump() for e in body.entries]))


@router.get("/search")
async def search_logs(
    tenant_id: str = Depends(get_current_tenant_id),
    level: str | None = None,
    service_name: str | None = None,
    correlation_id: str | None = None,
    trace_id: str | None = None,
    user_id: str | None = None,
    text_query: str | None = None,
    start_time: datetime | None = None,
    end_time: datetime | None = None,
    limit: int | None = None,
    service: LogSearchService = Depends(get_log_search_service),
):
    return to_dict_list(await service.search(
        tenant_id, level=level, service_name=service_name, correlation_id=correlation_id, trace_id=trace_id,
        user_id=user_id, text_query=text_query, start_time=start_time, end_time=end_time, limit=limit,
    ))


@router.get("/correlation/{correlation_id}")
async def logs_by_correlation_id(
    correlation_id: str, tenant_id: str = Depends(get_current_tenant_id), service: LogSearchService = Depends(get_log_search_service)
):
    return to_dict_list(await service.by_correlation_id(tenant_id, correlation_id))


@router.get("/trace/{trace_id}")
async def logs_by_trace_id(
    trace_id: str, tenant_id: str = Depends(get_current_tenant_id), service: LogSearchService = Depends(get_log_search_service)
):
    return to_dict_list(await service.by_trace_id(tenant_id, trace_id))


@router.get("/level-counts")
async def level_counts(
    tenant_id: str = Depends(get_current_tenant_id),
    start_time: datetime | None = None,
    service: LogSearchService = Depends(get_log_search_service),
):
    return await service.level_counts(tenant_id, start_time=start_time)


@router.post("/retention/sweep")
async def sweep_retention(
    tenant_id: str = Depends(get_current_tenant_id), service: LogRetentionService = Depends(get_log_retention_service)
):
    return {"deleted": await service.sweep_expired(tenant_id)}
