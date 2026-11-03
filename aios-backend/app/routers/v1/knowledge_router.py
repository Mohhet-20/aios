from fastapi import APIRouter, Depends, Query, status

from app.dependencies.service_dependencies import get_knowledge_service
from app.schemas.knowledge import KnowledgeCollectionCreate, KnowledgeCollectionRead
from app.services.knowledge_service import KnowledgeService

router = APIRouter(prefix="/knowledge", tags=["Knowledge Base"])


@router.post("/collections", response_model=KnowledgeCollectionRead, status_code=status.HTTP_201_CREATED)
async def create_collection(
    payload: KnowledgeCollectionCreate, service: KnowledgeService = Depends(get_knowledge_service)
):
    from app.models.knowledge import KnowledgeCollectionModel

    collection = KnowledgeCollectionModel(workspace_id=payload.workspace_id, name=payload.name)
    return await service.create(collection)


@router.get("/collections", response_model=list[KnowledgeCollectionRead])
async def list_collections(
    workspace_id: str | None = Query(default=None), service: KnowledgeService = Depends(get_knowledge_service)
):
    return await service.list(workspace_id=workspace_id) if workspace_id else await service.list()
