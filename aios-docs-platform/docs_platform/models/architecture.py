"""Architecture Portal schema: a diagram registry across the seven
diagram types the prompt specifies, plus tech-stack entries."""
from __future__ import annotations

from sqlalchemy import JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from docs_platform.database.base import AuditMixin, Base, IdMixin, SoftDeleteMixin


class DiagramModel(IdMixin, AuditMixin, SoftDeleteMixin, Base):
    __tablename__ = "doc_diagrams"

    tenant_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    diagram_type: Mapped[str] = mapped_column(String(25), nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(300), nullable=False)
    description: Mapped[str] = mapped_column(String(1000), nullable=False, default="")
    content: Mapped[str] = mapped_column(Text, nullable=False, default="")
    related_refs: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    version: Mapped[str] = mapped_column(String(30), nullable=False, default="v1")


class TechStackEntryModel(IdMixin, AuditMixin, Base):
    __tablename__ = "doc_tech_stack_entries"

    tenant_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    category: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    version_info: Mapped[str] = mapped_column(String(100), nullable=False, default="")
    description: Mapped[str] = mapped_column(String(1000), nullable=False, default="")
