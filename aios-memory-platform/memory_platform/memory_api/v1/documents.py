"""Document Intelligence: upload + process (real extraction/chunking/
classification/embedding) for PDF/DOCX/PPTX/XLSX/CSV/Markdown/HTML/JSON/
text, with lineage and status tracked throughout."""
from __future__ import annotations

from fastapi import APIRouter, Depends, File, Form, UploadFile

from memory_platform.document_processing.pipeline import DocumentProcessingService
from memory_platform.domain.enums import DocumentType
from memory_platform.memory_api.dependencies import get_current_actor_id, get_document_processing_service
from memory_platform.memory_api.serialization import to_dict, to_dict_list

router = APIRouter(prefix="/workspaces/{workspace_id}/documents", tags=["documents"])


@router.post("/upload", status_code=201)
async def upload_and_process_document(
    workspace_id: str, file: UploadFile = File(...), document_type: DocumentType = Form(...), title: str | None = Form(default=None),
    knowledge_base_id: str | None = Form(default=None), classify: bool = Form(default=True), generate_embeddings: bool = Form(default=True),
    actor_id: str = Depends(get_current_actor_id), svc: DocumentProcessingService = Depends(get_document_processing_service),
):
    raw_bytes = await file.read()
    document = await svc.upload_document(
        workspace_id=workspace_id, title=title or file.filename or "Untitled", document_type=document_type, uploaded_by=actor_id,
        filename=file.filename, knowledge_base_id=knowledge_base_id, mime_type=file.content_type, size_bytes=len(raw_bytes),
    )
    processed = await svc.process_document(document.id, raw_bytes, classify=classify, generate_embeddings=generate_embeddings)
    return to_dict(processed)


@router.get("")
async def list_documents(workspace_id: str, status: str | None = None, svc: DocumentProcessingService = Depends(get_document_processing_service)):
    return to_dict_list(await svc.list_documents(workspace_id, status=status))


@router.get("/{document_id}")
async def get_document(workspace_id: str, document_id: str, svc: DocumentProcessingService = Depends(get_document_processing_service)):
    return to_dict(await svc.get_document(document_id))


@router.get("/{document_id}/chunks")
async def list_document_chunks(workspace_id: str, document_id: str, svc: DocumentProcessingService = Depends(get_document_processing_service)):
    return to_dict_list(await svc.list_chunks(document_id))
