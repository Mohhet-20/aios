"""Vector Platform: embedding generation, batch indexing, incremental
updates, embedding versioning, similarity search, and index health —
the abstraction layer every future vector database swaps in behind."""
from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from memory_platform.memory_api.dependencies import get_vector_platform_service
from memory_platform.memory_api.serialization import to_dict, to_dict_list
from memory_platform.vector_store.vector_platform_service import VectorPlatformService

router = APIRouter(prefix="/workspaces/{workspace_id}/vectors", tags=["vectors"])


class EmbedItemsRequest(BaseModel):
    source_type: str
    items: list[tuple[str, str, dict[str, Any]]]
    vector_store_index: str = "default"


class IncrementalUpdateRequest(BaseModel):
    source_type: str
    source_id: str
    text: str
    metadata: dict | None = None
    vector_store_index: str = "default"


class DeleteFromIndexRequest(BaseModel):
    source_type: str
    source_ids: list[str]


@router.post("/index", status_code=201)
async def embed_and_index(workspace_id: str, body: EmbedItemsRequest, svc: VectorPlatformService = Depends(get_vector_platform_service)):
    records = await svc.embed_and_index(workspace_id=workspace_id, source_type=body.source_type, items=body.items, vector_store_index=body.vector_store_index)
    return to_dict_list(records)


@router.put("/index/item")
async def incremental_update(workspace_id: str, body: IncrementalUpdateRequest, svc: VectorPlatformService = Depends(get_vector_platform_service)):
    return to_dict(await svc.incremental_update(workspace_id=workspace_id, source_type=body.source_type, source_id=body.source_id, text=body.text, metadata=body.metadata, vector_store_index=body.vector_store_index))


@router.post("/index/item/reindex", status_code=201)
async def reindex_with_version_bump(workspace_id: str, body: IncrementalUpdateRequest, svc: VectorPlatformService = Depends(get_vector_platform_service)):
    return to_dict(await svc.reindex_with_version_bump(workspace_id=workspace_id, source_type=body.source_type, source_id=body.source_id, text=body.text, metadata=body.metadata, vector_store_index=body.vector_store_index))


@router.get("/search")
async def similarity_search(workspace_id: str, query: str, top_k: int = 10, svc: VectorPlatformService = Depends(get_vector_platform_service)):
    matches = await svc.similarity_search_query(query, top_k=top_k)
    return [{"id": m.id, "score": m.score, "metadata": m.metadata} for m in matches]


@router.post("/index/delete")
async def delete_from_index(workspace_id: str, body: DeleteFromIndexRequest, svc: VectorPlatformService = Depends(get_vector_platform_service)):
    deleted = await svc.delete_from_index(body.source_type, body.source_ids)
    return {"deleted_count": deleted}


@router.get("/indexes")
async def list_indexes(workspace_id: str, svc: VectorPlatformService = Depends(get_vector_platform_service)):
    return await svc.list_indexes(workspace_id)


@router.get("/indexes/{vector_store_index}/health")
async def index_health(workspace_id: str, vector_store_index: str, svc: VectorPlatformService = Depends(get_vector_platform_service)):
    return to_dict(await svc.index_health(vector_store_index))
