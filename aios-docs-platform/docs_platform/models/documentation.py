"""Documentation Core schema: spaces (a named grouping of pages within
one of the 15 doc types the prompt specifies) and pages, guarded
through the editorial draft -> in_review -> published ->
archived/deprecated lifecycle."""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from docs_platform.database.base import AuditMixin, Base, IdMixin, SoftDeleteMixin


class DocSpaceModel(IdMixin, AuditMixin, SoftDeleteMixin, Base):
    __tablename__ = "doc_spaces"

    tenant_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    key: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    doc_type: Mapped[str] = mapped_column(String(25), nullable=False, index=True)
    description: Mapped[str | None] = mapped_column(String(1000), nullable=True)


class DocPageModel(IdMixin, AuditMixin, SoftDeleteMixin, Base):
    __tablename__ = "doc_pages"

    tenant_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    space_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(300), nullable=False)
    slug: Mapped[str] = mapped_column(String(300), nullable=False, index=True)
    doc_type: Mapped[str] = mapped_column(String(25), nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(15), nullable=False, default="draft", index=True)
    content: Mapped[str] = mapped_column(Text, nullable=False, default="")
    owner_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    visibility: Mapped[str] = mapped_column(String(10), nullable=False, default="internal", index=True)
    current_version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    last_reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
