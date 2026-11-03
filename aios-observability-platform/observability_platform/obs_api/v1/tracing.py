"""Distributed tracing API: span ingestion, trace lifecycle, tree
reconstruction, integrity checking, and trace-derived dependency
graphs."""
from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from observability_platform.dependencies.dependencies import (
    get_current_tenant_id,
    get_span_service,
    get_trace_dependency_service,
    get_trace_service,
)
from observability_platform.obs_api.serialization import to_dict, to_dict_list
from observability_platform.tracing.dependency_service import TraceDependencyService
from observability_platform.tracing.span_service import SpanService
from observability_platform.tracing.trace_service import TraceService

router = APIRouter(prefix="/traces", tags=["tracing"])


class StartSpanRequest(BaseModel):
    span_id: str
    service_name: str
    operation_name: str
    parent_span_id: str | None = None
    span_kind: str = "internal"
    attributes: dict | None = None
    start_time: datetime | None = None


@router.post("/{trace_id}/spans", status_code=201)
async def start_span(
    trace_id: str, body: StartSpanRequest, tenant_id: str = Depends(get_current_tenant_id), service: SpanService = Depends(get_span_service)
):
    return to_dict(await service.start_span(tenant_id, trace_id=trace_id, **body.model_dump()))


class EndSpanRequest(BaseModel):
    status: str = "ok"
    end_time: datetime | None = None
    attributes_update: dict | None = None


@router.post("/{trace_id}/spans/{span_id}/end")
async def end_span(
    trace_id: str, span_id: str, body: EndSpanRequest,
    tenant_id: str = Depends(get_current_tenant_id), service: SpanService = Depends(get_span_service),
):
    spans = await service.list_for_trace(tenant_id, trace_id)
    span = next(s for s in spans if s.span_id == span_id)
    return to_dict(await service.end_span(tenant_id, span, **body.model_dump()))


@router.get("/{trace_id}/spans")
async def list_spans(trace_id: str, tenant_id: str = Depends(get_current_tenant_id), service: SpanService = Depends(get_span_service)):
    return to_dict_list(await service.list_for_trace(tenant_id, trace_id))


@router.post("/{trace_id}/finalize")
async def finalize_trace(trace_id: str, tenant_id: str = Depends(get_current_tenant_id), service: TraceService = Depends(get_trace_service)):
    return to_dict(await service.finalize_trace(tenant_id, trace_id))


@router.get("/{trace_id}/tree")
async def span_tree(trace_id: str, tenant_id: str = Depends(get_current_tenant_id), service: TraceService = Depends(get_trace_service)):
    return await service.build_span_tree(tenant_id, trace_id)


@router.get("/{trace_id}/integrity")
async def check_integrity(trace_id: str, tenant_id: str = Depends(get_current_tenant_id), service: TraceService = Depends(get_trace_service)):
    return {"orphan_span_ids": await service.check_integrity(tenant_id, trace_id)}


@router.get("/{trace_id}/dependencies")
async def trace_dependencies(
    trace_id: str, tenant_id: str = Depends(get_current_tenant_id), service: TraceDependencyService = Depends(get_trace_dependency_service)
):
    return await service.service_dependencies_from_trace(tenant_id, trace_id)


@router.get("/dependencies/recent")
async def recent_dependencies(
    tenant_id: str = Depends(get_current_tenant_id), limit: int = 100,
    service: TraceDependencyService = Depends(get_trace_dependency_service),
):
    return await service.service_dependencies_from_recent_traces(tenant_id, limit=limit)
