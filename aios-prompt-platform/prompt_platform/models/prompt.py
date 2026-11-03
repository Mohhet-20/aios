"""The Prompt aggregate root and its library metadata (tags, categories,
favorites). `Prompt` itself holds no template text — that lives on
`PromptVersion` (models/version.py); a Prompt is the stable identity/
metadata container a version history hangs off of, mirroring how source
control treats a file's path vs. its commit history.
"""
from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import JSON, DateTime, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from prompt_platform.database.base import AuditMixin, Base, IdMixin, SoftDeleteMixin, VersionedMixin, utcnow
from prompt_platform.domain.enums import PromptStatus, PromptVisibility

if TYPE_CHECKING:
    from prompt_platform.models.version import PromptVersionModel


class PromptModel(Base, IdMixin, AuditMixin, SoftDeleteMixin, VersionedMixin):
    __tablename__ = "prompts"

    project_id: Mapped[str] = mapped_column(String(36), ForeignKey("prompt_projects.id"), nullable=False, index=True)
    workspace_id: Mapped[str] = mapped_column(String(36), ForeignKey("prompt_workspaces.id"), nullable=False, index=True)

    name: Mapped[str] = mapped_column(String(200), nullable=False)
    slug: Mapped[str] = mapped_column(String(220), nullable=False, index=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    status: Mapped[str] = mapped_column(String(20), default=PromptStatus.DRAFT.value, nullable=False)
    visibility: Mapped[str] = mapped_column(String(20), default=PromptVisibility.PRIVATE.value, nullable=False)
    category_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("prompt_categories.id"), nullable=True)

    owner_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)

    latest_version_number: Mapped[int] = mapped_column(default=0, nullable=False)
    production_version_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    stable_version_id: Mapped[str | None] = mapped_column(String(36), nullable=True)

    is_template: Mapped[bool] = mapped_column(default=False, nullable=False)
    sensitive: Mapped[bool] = mapped_column(default=False, nullable=False, doc="Governance flag for restricted-access prompts")

    tags_cache: Mapped[list] = mapped_column(JSON, default=list, nullable=False, doc="Denormalized tag names for fast list-view search")

    versions: Mapped[list[PromptVersionModel]] = relationship(back_populates="prompt", foreign_keys="PromptVersionModel.prompt_id")


class PromptCategoryModel(Base, IdMixin, AuditMixin):
    __tablename__ = "prompt_categories"

    name: Mapped[str] = mapped_column(String(120), nullable=False)
    slug: Mapped[str] = mapped_column(String(140), nullable=False, index=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)


class PromptTagModel(Base, IdMixin):
    __tablename__ = "prompt_tags"

    name: Mapped[str] = mapped_column(String(80), nullable=False, unique=True)
    slug: Mapped[str] = mapped_column(String(100), nullable=False, index=True)


class PromptTagLinkModel(Base):
    __tablename__ = "prompt_tag_links"

    prompt_id: Mapped[str] = mapped_column(String(36), ForeignKey("prompts.id"), primary_key=True)
    tag_id: Mapped[str] = mapped_column(String(36), ForeignKey("prompt_tags.id"), primary_key=True)


class PromptFavoriteModel(Base, IdMixin):
    __tablename__ = "prompt_favorites"

    user_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    prompt_id: Mapped[str] = mapped_column(String(36), ForeignKey("prompts.id"), nullable=False, index=True)
    created_at = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
