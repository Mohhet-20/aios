from sqlalchemy import Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import AuditMixin, Base, IdMixin, SoftDeleteMixin


class KnowledgeCollectionModel(IdMixin, AuditMixin, SoftDeleteMixin, Base):
    __tablename__ = "knowledge_collections"

    workspace_id: Mapped[str] = mapped_column(String(36), index=True, nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    document_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)


class DocumentModel(IdMixin, AuditMixin, SoftDeleteMixin, Base):
    __tablename__ = "documents"

    workspace_id: Mapped[str] = mapped_column(String(36), index=True, nullable=False)
    collection_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    name: Mapped[str] = mapped_column(String(500), nullable=False)
    size_bytes: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    status: Mapped[str] = mapped_column(String(32), default="pending", nullable=False)
    storage_uri: Mapped[str] = mapped_column(String(1000), default="", nullable=False)
