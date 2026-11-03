"""DocumentProcessingService — the ingestion pipeline: create the
document record, extract text (real extractors), chunk it intelligently
(token-aware, boundary-respecting), generate metadata, optionally
classify content and create embeddings via the AI Core, and track
lineage/processing history the whole way — one orchestrator so no
caller has to hand-sequence these steps itself.
"""
from __future__ import annotations

from datetime import datetime

from ai_core.bootstrap import AICoreContext
from ai_core.schemas.requests import EmbeddingRequest

from memory_platform.config.settings import Settings, get_settings
from memory_platform.core.exceptions import DocumentProcessingError
from memory_platform.database.base import new_uuid
from memory_platform.document_processing import extractors
from memory_platform.document_processing.chunking import chunk_text
from memory_platform.document_processing.classification import classify_document
from memory_platform.domain.enums import DocumentStatus, DocumentType
from memory_platform.models.document import DocumentChunkModel, DocumentModel
from memory_platform.models.embedding_record import EmbeddingRecordModel
from memory_platform.repositories.registry import RepositoryRegistry
from memory_platform.clock import utc_now


def _now() -> datetime:
    return utc_now()


class DocumentProcessingService:
    def __init__(self, repos: RepositoryRegistry, *, ai_core: AICoreContext | None = None, settings: Settings | None = None, transcription_provider=None):
        self.repos = repos
        self.ai_core = ai_core
        self.settings = settings or get_settings()
        self.transcription_provider = transcription_provider

    def _append_lineage(self, model: DocumentModel, step: str, *, parent_document_id: str | None = None) -> None:
        lineage = dict(model.lineage or {})
        history = list(lineage.get("processing_history", []))
        history.append({"step": step, "at": _now().isoformat()})
        lineage["processing_history"] = history
        if parent_document_id is not None:
            lineage["parent_document_id"] = parent_document_id
        model.lineage = lineage

    async def upload_document(
        self, *, workspace_id: str, title: str, document_type: DocumentType | str, uploaded_by: str,
        filename: str | None = None, knowledge_base_id: str | None = None, source_uri: str | None = None,
        mime_type: str | None = None, size_bytes: int | None = None, parent_document_id: str | None = None,
    ) -> DocumentModel:
        dtype = document_type.value if isinstance(document_type, DocumentType) else document_type
        model = DocumentModel(
            id=new_uuid(), workspace_id=workspace_id, knowledge_base_id=knowledge_base_id, title=title, filename=filename,
            document_type=dtype, source_uri=source_uri, mime_type=mime_type, size_bytes=size_bytes,
            uploaded_by=uploaded_by, status=DocumentStatus.PENDING.value,
        )
        self._append_lineage(model, "uploaded", parent_document_id=parent_document_id)
        return await self.repos.documents.add(model)

    async def process_document(
        self, document_id: str, raw_bytes: bytes, *, classify: bool = True, generate_embeddings: bool = True, vector_store_index: str = "default",
    ) -> DocumentModel:
        model = await self.repos.documents.get_or_404(document_id)
        model.status = DocumentStatus.PROCESSING.value
        await self.repos.documents.update(model)

        try:
            extraction = extractors.extract(model.document_type, raw_bytes, filename=model.filename, transcription_provider=self.transcription_provider)
            self._append_lineage(model, "extracted")
            model.page_count = extraction.page_count
            model.extracted_text_length = len(extraction.text)

            chunks = chunk_text(
                extraction.text, max_tokens=self.settings.document_chunk_max_tokens, overlap_tokens=self.settings.document_chunk_overlap_tokens,
            )
            chunk_models: list[DocumentChunkModel] = []
            for c in chunks:
                chunk_models.append(await self.repos.document_chunks.add(DocumentChunkModel(
                    id=new_uuid(), document_id=model.id, chunk_index=c.chunk_index, content=c.content,
                    token_count=c.token_count, start_offset=c.start_offset, end_offset=c.end_offset,
                )))
            self._append_lineage(model, f"chunked:{len(chunk_models)}_chunks")

            if classify and self.ai_core is not None and extraction.text.strip():
                classification = await classify_document(self.ai_core, extraction.text)
                model.classification = classification.model_dump()
                model.language = classification.language
                self._append_lineage(model, "classified")

            if generate_embeddings and self.ai_core is not None and chunk_models:
                await self._embed_chunks(model.workspace_id, chunk_models, vector_store_index=vector_store_index)
                self._append_lineage(model, f"embedded:{len(chunk_models)}_chunks")

            model.status = DocumentStatus.PROCESSED.value
            model.processed_at = _now()
            model.error_message = None
            await self.repos.documents.update(model)
            return model
        except Exception as exc:  # noqa: BLE001
            model.status = DocumentStatus.FAILED.value
            model.error_message = str(exc)
            self._append_lineage(model, "failed")
            await self.repos.documents.update(model)
            if isinstance(exc, DocumentProcessingError):
                raise
            raise DocumentProcessingError(f"Document processing failed for '{document_id}': {exc}") from exc

    async def _embed_chunks(self, workspace_id: str, chunk_models: list[DocumentChunkModel], *, vector_store_index: str) -> None:
        """Embeds every chunk (one batched call) and both persists our own
        durable `EmbeddingRecordModel` metadata and upserts the actual
        vector into the AI Core's `VectorStore`. `vector_store_index` is a
        *logical* index tag recorded on the metadata row — the physical
        store itself is flat today; the Vector Platform (built on top of
        this same embedding path) is what gives that tag real multi-index
        query-time meaning."""
        from ai_core.embeddings.vector_store import VectorRecord

        texts = [c.content for c in chunk_models]
        response = await self.ai_core.embedding_engine.embed(EmbeddingRequest(input=texts))
        records_to_upsert = []
        for chunk_model, vector in zip(chunk_models, response.embeddings):
            record = await self.repos.embedding_records.add(EmbeddingRecordModel(
                id=new_uuid(), workspace_id=workspace_id, source_type="document_chunk", source_id=chunk_model.id,
                vector_store_index=vector_store_index, model=response.model, provider=response.provider, dimensions=len(vector),
            ))
            chunk_model.embedding_id = record.id
            await self.repos.document_chunks.update(chunk_model)
            records_to_upsert.append(VectorRecord(id=chunk_model.id, vector=vector, metadata={"document_id": chunk_model.document_id, "index": vector_store_index}))
        if records_to_upsert and self.ai_core.vector_store is not None:
            await self.ai_core.vector_store.upsert(records_to_upsert)

    async def get_document(self, document_id: str) -> DocumentModel:
        return await self.repos.documents.get_or_404(document_id)

    async def list_chunks(self, document_id: str) -> list[DocumentChunkModel]:
        return await self.repos.document_chunks.list_for_document(document_id)

    async def list_documents(self, workspace_id: str, *, status: str | None = None) -> list[DocumentModel]:
        return await self.repos.documents.list_by_workspace(workspace_id, status=status)
