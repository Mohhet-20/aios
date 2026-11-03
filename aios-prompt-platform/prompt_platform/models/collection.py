"""Prompt Collections — user-curated groupings of prompts, distinct from
`PromptCategory` (a single-label taxonomy each prompt belongs to at most
one of) and from tags (many-to-many free-form labels). A collection is
closer to a folder/playlist: "prompts for Q3 onboarding," "my favorites
for code review," etc.
"""
from __future__ import annotations

from sqlalchemy import ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from prompt_platform.database.base import AuditMixin, Base, IdMixin, SoftDeleteMixin


class PromptCollectionModel(Base, IdMixin, AuditMixin, SoftDeleteMixin):
    __tablename__ = "prompt_collections"

    workspace_id: Mapped[str] = mapped_column(String(36), ForeignKey("prompt_workspaces.id"), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    owner_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    is_shared: Mapped[bool] = mapped_column(default=False, nullable=False, doc="Visible to the whole workspace, not just the owner")


class PromptCollectionItemModel(Base, IdMixin):
    __tablename__ = "prompt_collection_items"

    collection_id: Mapped[str] = mapped_column(String(36), ForeignKey("prompt_collections.id"), nullable=False, index=True)
    prompt_id: Mapped[str] = mapped_column(String(36), ForeignKey("prompts.id"), nullable=False, index=True)
