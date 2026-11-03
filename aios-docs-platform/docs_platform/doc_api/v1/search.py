"""Enterprise Search: keyword/full-text search across published pages
and KB articles, click logging, and recent/failed/popular-query
analytics. Ranked tuple results are serialized as {"ref": ...,
"score": ...}, popular-query tuples as {"query": ..., "count": ...}."""
from __future__ import annotations

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from docs_platform.dependencies.dependencies import get_current_tenant_id, get_search_service
from docs_platform.doc_api.serialization import to_dict, to_dict_list
from docs_platform.search.search_service import SearchService

router = APIRouter(prefix="/search", tags=["search"])


@router.get("")
async def search(
    q: str, doc_type: str | None = None, limit: int | None = None,
    tenant_id: str = Depends(get_current_tenant_id), service: SearchService = Depends(get_search_service),
):
    results = await service.search(tenant_id, q, doc_type=doc_type, limit=limit)
    return [{"ref": ref, "score": score} for ref, score in results]


class RecordClickRequest(BaseModel):
    doc_ref: str


@router.post("/{query_log_id}/click")
async def record_click(
    query_log_id: str, body: RecordClickRequest, tenant_id: str = Depends(get_current_tenant_id), service: SearchService = Depends(get_search_service),
):
    return to_dict(await service.record_click(tenant_id, query_log_id, body.doc_ref))


@router.get("/recent-queries")
async def recent_queries(
    limit: int = 20, tenant_id: str = Depends(get_current_tenant_id), service: SearchService = Depends(get_search_service),
):
    return to_dict_list(await service.recent_queries(tenant_id, limit=limit))


@router.get("/failed-searches")
async def failed_searches(
    limit: int = 20, tenant_id: str = Depends(get_current_tenant_id), service: SearchService = Depends(get_search_service),
):
    return to_dict_list(await service.failed_searches(tenant_id, limit=limit))


@router.get("/popular-queries")
async def popular_queries(
    limit: int = 10, sample_size: int = 500,
    tenant_id: str = Depends(get_current_tenant_id), service: SearchService = Depends(get_search_service),
):
    results = await service.popular_queries(tenant_id, limit=limit, sample_size=sample_size)
    return [{"query": query, "count": count} for query, count in results]
