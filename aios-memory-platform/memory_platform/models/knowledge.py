"""Knowledge Management: curated, owned, reviewed knowledge — distinct
from raw agent memory (ephemeral, agent-scoped recall). A KnowledgeBase
groups Collections, which group Items; every Item goes through a real
draft -> in_review -> published lifecycle with an append-only version
history."""
from __future__ import annotations

from sqlalchemy import JSON, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from memory_platform.database.base import AuditMixin, Base, IdMixin, utcnow
from memory_platform.domain.enums import KnowledgeItemStatus


class KnowledgeBaseModel(Base, IdMixin, AuditMixin):
    __tablename__ = "mem_knowledge_bases"

    workspace_id: Mapped[str] = mapped_column(String(36), ForeignKey("mem_workspaces.id"), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    slug: Mapped[str] = mapped_column(String(220), nullable=False, index=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    owner_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)


class KnowledgeCollectionModel(Base, IdMixin, AuditMixin):
    __tablename__ = "mem_knowledge_collections"

    knowledge_base_id: Mapped[str] = mapped_column(String(36), ForeignKey("mem_knowledge_bases.id"), nullable=False, index=True)
    parent_collection_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("mem_knowledge_collections.id"), nullable=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    slug: Mapped[str] = mapped_column(String(220), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)


class KnowledgeItemModel(Base, IdMixin, AuditMixin):
    __tablename__ = "mem_knowledge_items"

    workspace_id: Mapped[str] = mapped_column(String(36), ForeignKey("mem_workspaces.id"), nullable=False, index=True)
    knowledge_base_id: Mapped[str] = mapped_column(String(36), ForeignKey("mem_knowledge_bases.id"), nullable=False, index=True)
    collection_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("mem_knowledge_collections.id"), nullable=True, index=True)
    source_document_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("mem_documents.id"), nullable=True)

    title: Mapped[str] = mapped_column(String(300), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    category: Mapped[str | None] = mapped_column(String(120), nullable=True, index=True)
    tags: Mapped[list] = mapped_column(JSON, default=list, nullable=False)

    embedding_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("mem_embedding_records.id"), nullable=True)

    owner_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(20), default=KnowledgeItemStatus.DRAFT.value, nullable=False)
    version: Mapped[int] = mapped_column(Integer, default=1, nullable=False)

    reviewed_by: Mapped[str | None] = mapped_column(String(36), nullable=True)
    reviewed_at: Mapped[object | None] = mapped_column(DateTime(timezone=True), nullable=True)
    published_at: Mapped[object | None] = mapped_column(DateTime(timezone=True), nullable=True)


class KnowledgeItemVersionModel(Base, IdMixin):
    """Append-only version history — never updated or deleted, only added to."""

    __tablename__ = "mem_knowledge_item_versions"

    knowledge_item_id: Mapped[str] = mapped_column(String(36), ForeignKey("mem_knowledge_items.id"), nullable=False, index=True)
    version_number: Mapped[int] = mapped_column(Integer, nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    changed_by: Mapped[str] = mapped_column(String(36), nullable=False)
    change_note: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
