"""Knowledge Base schema: articles across the nine article types the
prompt specifies (how-to, best practice, troubleshooting, FAQ, release
note, migration guide, design pattern, reference, glossary)."""
from __future__ import annotations

from sqlalchemy import JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from docs_platform.database.base import AuditMixin, Base, IdMixin, SoftDeleteMixin


class KbArticleModel(IdMixin, AuditMixin, SoftDeleteMixin, Base):
    __tablename__ = "doc_kb_articles"

    tenant_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    article_type: Mapped[str] = mapped_column(String(25), nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(300), nullable=False)
    slug: Mapped[str] = mapped_column(String(300), nullable=False, index=True)
    content: Mapped[str] = mapped_column(Text, nullable=False, default="")
    tags: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    status: Mapped[str] = mapped_column(String(15), nullable=False, default="draft", index=True)
    owner_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
