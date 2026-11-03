"""Cache Platform: multi-level get/set/invalidate plus per-layer stats."""
from __future__ import annotations

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from perf_platform.caching.cache_service import CacheService
from perf_platform.dependencies.dependencies import get_cache_service, get_current_tenant_id
from perf_platform.perf_api.serialization import to_dict, to_dict_list

router = APIRouter(prefix="/cache", tags=["cache"])


class SetCacheEntryRequest(BaseModel):
    layer: str
    key: str
    value: str
    ttl_seconds: int | None = None


@router.put("/entries")
async def set_entry(
    body: SetCacheEntryRequest, tenant_id: str = Depends(get_current_tenant_id), service: CacheService = Depends(get_cache_service),
):
    return to_dict(await service.set(tenant_id, body.layer, body.key, body.value, ttl_seconds=body.ttl_seconds))


@router.get("/entries/{layer}/{key}")
async def get_entry(
    layer: str, key: str, tenant_id: str = Depends(get_current_tenant_id), service: CacheService = Depends(get_cache_service),
):
    value = await service.get(tenant_id, layer, key)
    return {"layer": layer, "key": key, "value": value, "found": value is not None}


@router.delete("/entries/{layer}/{key}")
async def invalidate_entry(
    layer: str, key: str, tenant_id: str = Depends(get_current_tenant_id), service: CacheService = Depends(get_cache_service),
):
    return {"invalidated": await service.invalidate(tenant_id, layer, key)}


@router.get("/stats")
async def stats(tenant_id: str = Depends(get_current_tenant_id), service: CacheService = Depends(get_cache_service)):
    return to_dict_list(await service.stats(tenant_id))


@router.post("/sweep")
async def sweep_expired(tenant_id: str = Depends(get_current_tenant_id), service: CacheService = Depends(get_cache_service)):
    return {"removed": await service.sweep_expired(tenant_id)}
