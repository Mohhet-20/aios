from fastapi import APIRouter, Depends, Query, status

from app.dependencies.service_dependencies import get_document_service
from app.schemas.knowledge import DocumentRead, DocumentUploadRequest
from app.services.knowledge_service import DocumentService

router = APIRouter(prefix="/documents", tags=["Documents"])


@router.post("", response_model=DocumentRead, status_code=status.HTTP_202_ACCEPTED)
async def upload_document(
    payload: DocumentUploadRequest, service: DocumentService = Depends(get_document_service)
):
    return await service.upload(payload.workspace_id, payload.name, payload.size_bytes, payload.collection_id)


@router.get("", response_model=list[DocumentRead])
async def list_documents(
    workspace_id: str | None = Query(default=None), service: DocumentService = Depends(get_document_service)
):
    return await service.list(workspace_id=workspace_id) if workspace_id else await service.list()


@router.get("/{document_id}", response_model=DocumentRead)
async def get_document(document_id: str, service: DocumentService = Depends(get_document_service)):
    return await service.get(document_id)
