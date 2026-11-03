"""DocumentModel: the source-file record and its full processing/lineage
history; DocumentChunkModel: the intelligently-chunked, embeddable units
extracted from it. `lineage` tracks parent/derived-from relationships
(e.g. a summarized document derived from an original) directly on the
row for O(1) lookups without a graph traversal for the common case."""
from __future__ import annotations

from sqlalchemy import JSON, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from memory_platform.database.base import AuditMixin, Base, IdMixin, utcnow
from memory_platform.domain.enums import DocumentStatus


class DocumentModel(Base, IdMixin, AuditMixin):
    __tablename__ = "mem_documents"

    workspace_id: Mapped[str] = mapped_column(String(36), ForeignKey("mem_workspaces.id"), nullable=False, index=True)
    knowledge_base_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("mem_knowledge_bases.id"), nullable=True, index=True)

    title: Mapped[str] = mapped_column(String(300), nullable=False)
    filename: Mapped[str | None] = mapped_column(String(300), nullable=True)
    document_type: Mapped[str] = mapped_column(String(20), nullable=False)
    source_uri: Mapped[str | None] = mapped_column(String(1000), nullable=True, doc="e.g. a web URL for WEBPAGE documents")
    mime_type: Mapped[str | None] = mapped_column(String(120), nullable=True)
    size_bytes: Mapped[int | None] = mapped_column(Integer, nullable=True)

    uploaded_by: Mapped[str] = mapped_column(String(36), nullable=False)
    status: Mapped[str] = mapped_column(String(20), default=DocumentStatus.PENDING.value, nullable=False)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)

    page_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    extracted_text_length: Mapped[int | None] = mapped_column(Integer, nullable=True)
    language: Mapped[str | None] = mapped_column(String(20), nullable=True)
    classification: Mapped[dict | None] = mapped_column(JSON, nullable=True, doc="{categories, topics, confidence} from LLM classification")
    lineage: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False, doc="{parent_document_id, derived_from, processing_history: [...]}")

    processed_at: Mapped[object | None] = mapped_column(DateTime(timezone=True), nullable=True)


class DocumentChunkModel(Base, IdMixin):
    __tablename__ = "mem_document_chunks"

    document_id: Mapped[str] = mapped_column(String(36), ForeignKey("mem_documents.id"), nullable=False, index=True)
    chunk_index: Mapped[int] = mapped_column(Integer, nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    token_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    embedding_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("mem_embedding_records.id"), nullable=True)
    start_offset: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    end_offset: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    chunk_metadata: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    created_at = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
