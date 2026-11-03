"""Knowledge Management: knowledge bases -> collections -> items, the
full draft/review/publish workflow, version history, search, and
relationship linking against the shared Knowledge Graph substrate."""
from __future__ import annotations

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from memory_platform.memory_api.dependencies import get_current_actor_id, get_knowledge_service
from memory_platform.memory_api.serialization import to_dict, to_dict_list
from memory_platform.knowledge.knowledge_service import KnowledgeService

router = APIRouter(prefix="/workspaces/{workspace_id}/knowledge", tags=["knowledge"])


class CreateKnowledgeBaseRequest(BaseModel):
    name: str
    slug: str
    description: str | None = None


class CreateCollectionRequest(BaseModel):
    knowledge_base_id: str
    name: str
    slug: str
    parent_collection_id: str | None = None
    description: str | None = None


class CreateItemRequest(BaseModel):
    knowledge_base_id: str
    title: str
    content: str
    collection_id: str | None = None
    category: str | None = None
    tags: list[str] | None = None
    source_document_id: str | None = None
    summary: str | None = None


class UpdateItemContentRequest(BaseModel):
    content: str
    summary: str | None = None
    change_note: str | None = None


class LinkRelatedRequest(BaseModel):
    related_item_id: str
    relation_type: str = "related_to"
    weight: float = 1.0


@router.post("/bases", status_code=201)
async def create_knowledge_base(workspace_id: str, body: CreateKnowledgeBaseRequest, actor_id: str = Depends(get_current_actor_id), svc: KnowledgeService = Depends(get_knowledge_service)):
    return to_dict(await svc.create_knowledge_base(workspace_id=workspace_id, name=body.name, slug=body.slug, owner_id=actor_id, description=body.description))


@router.post("/collections", status_code=201)
async def create_collection(workspace_id: str, body: CreateCollectionRequest, svc: KnowledgeService = Depends(get_knowledge_service)):
    return to_dict(await svc.create_collection(knowledge_base_id=body.knowledge_base_id, name=body.name, slug=body.slug, parent_collection_id=body.parent_collection_id, description=body.description))


@router.get("/bases/{knowledge_base_id}/collections")
async def list_collections(workspace_id: str, knowledge_base_id: str, svc: KnowledgeService = Depends(get_knowledge_service)):
    return to_dict_list(await svc.list_collections(knowledge_base_id))


@router.post("/items", status_code=201)
async def create_item(workspace_id: str, body: CreateItemRequest, actor_id: str = Depends(get_current_actor_id), svc: KnowledgeService = Depends(get_knowledge_service)):
    return to_dict(await svc.create_item(
        workspace_id=workspace_id, knowledge_base_id=body.knowledge_base_id, title=body.title, content=body.content, owner_id=actor_id,
        collection_id=body.collection_id, category=body.category, tags=body.tags, source_document_id=body.source_document_id, summary=body.summary,
    ))


@router.get("/items/search")
async def search_items(workspace_id: str, query: str, status: str | None = None, svc: KnowledgeService = Depends(get_knowledge_service)):
    return to_dict_list(await svc.search(workspace_id, query, status=status))


@router.get("/bases/{knowledge_base_id}/items")
async def list_items(workspace_id: str, knowledge_base_id: str, status: str | None = None, svc: KnowledgeService = Depends(get_knowledge_service)):
    return to_dict_list(await svc.list_by_knowledge_base(knowledge_base_id, status=status))


@router.get("/items/{item_id}")
async def get_item(workspace_id: str, item_id: str, svc: KnowledgeService = Depends(get_knowledge_service)):
    return to_dict(await svc.get(item_id))


@router.put("/items/{item_id}/content")
async def update_item_content(workspace_id: str, item_id: str, body: UpdateItemContentRequest, actor_id: str = Depends(get_current_actor_id), svc: KnowledgeService = Depends(get_knowledge_service)):
    return to_dict(await svc.update_content(item_id, content=body.content, changed_by=actor_id, summary=body.summary, change_note=body.change_note))


@router.get("/items/{item_id}/versions")
async def list_item_versions(workspace_id: str, item_id: str, svc: KnowledgeService = Depends(get_knowledge_service)):
    return to_dict_list(await svc.list_versions(item_id))


@router.post("/items/{item_id}/submit-for-review")
async def submit_item_for_review(workspace_id: str, item_id: str, svc: KnowledgeService = Depends(get_knowledge_service)):
    return to_dict(await svc.submit_for_review(item_id))


@router.post("/items/{item_id}/publish")
async def publish_item(workspace_id: str, item_id: str, actor_id: str = Depends(get_current_actor_id), svc: KnowledgeService = Depends(get_knowledge_service)):
    return to_dict(await svc.approve_and_publish(item_id, reviewed_by=actor_id))


@router.post("/items/{item_id}/reject")
async def reject_item(workspace_id: str, item_id: str, actor_id: str = Depends(get_current_actor_id), svc: KnowledgeService = Depends(get_knowledge_service)):
    return to_dict(await svc.reject(item_id, reviewed_by=actor_id))


@router.post("/items/{item_id}/deprecate")
async def deprecate_item(workspace_id: str, item_id: str, svc: KnowledgeService = Depends(get_knowledge_service)):
    return to_dict(await svc.deprecate(item_id))


@router.post("/items/{item_id}/archive")
async def archive_item(workspace_id: str, item_id: str, svc: KnowledgeService = Depends(get_knowledge_service)):
    return to_dict(await svc.archive(item_id))


@router.post("/items/{item_id}/related", status_code=201)
async def link_related_item(workspace_id: str, item_id: str, body: LinkRelatedRequest, svc: KnowledgeService = Depends(get_knowledge_service)):
    return to_dict(await svc.link_related(item_id, body.related_item_id, relation_type=body.relation_type, weight=body.weight))


@router.get("/items/{item_id}/related")
async def list_related_items(workspace_id: str, item_id: str, svc: KnowledgeService = Depends(get_knowledge_service)):
    return to_dict_list(await svc.list_related(item_id))
