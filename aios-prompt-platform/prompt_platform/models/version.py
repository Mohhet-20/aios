"""PromptVersion — the actual versioned, executable artifact — plus
dependency edges, an append-only change log, and release records."""
from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import JSON, DateTime, Float, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from prompt_platform.database.base import AuditMixin, Base, IdMixin, SoftDeleteMixin, VersionedMixin, utcnow
from prompt_platform.domain.enums import DependencyRelationship, VersionBranch, VersionStatus

if TYPE_CHECKING:
    from prompt_platform.models.prompt import PromptModel


class PromptVersionModel(Base, IdMixin, AuditMixin, SoftDeleteMixin, VersionedMixin):
    __tablename__ = "prompt_versions"

    prompt_id: Mapped[str] = mapped_column(String(36), ForeignKey("prompts.id"), nullable=False, index=True)
    version_number: Mapped[int] = mapped_column(nullable=False)
    parent_version_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("prompt_versions.id"), nullable=True)

    # Template content — split by role so the Studio can edit each
    # independently; rendered together into a ChatMessage list at execution
    # time via ai_core.prompts.composer.
    system_template: Mapped[str | None] = mapped_column(Text, nullable=True)
    developer_template: Mapped[str | None] = mapped_column(Text, nullable=True)
    user_template: Mapped[str] = mapped_column(Text, nullable=False)

    variables_schema: Mapped[list] = mapped_column(JSON, default=list, nullable=False, doc="[{name, type, description, required, default}]")
    parameters: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False, doc="model/provider/temperature/max_tokens/tools/response_format defaults")

    status: Mapped[str] = mapped_column(String(20), default=VersionStatus.DRAFT.value, nullable=False)
    branch: Mapped[str] = mapped_column(String(20), default=VersionBranch.EXPERIMENTAL.value, nullable=False)

    release_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    eval_score: Mapped[float | None] = mapped_column(Float, nullable=True)

    submitted_for_review_by: Mapped[str | None] = mapped_column(String(36), nullable=True)
    submitted_for_review_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    approved_by: Mapped[str | None] = mapped_column(String(36), nullable=True)
    approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    rejection_reason: Mapped[str | None] = mapped_column(Text, nullable=True)

    prompt: Mapped[PromptModel] = relationship(back_populates="versions", foreign_keys=[prompt_id])


class PromptDependencyModel(Base, IdMixin, AuditMixin):
    __tablename__ = "prompt_dependencies"

    prompt_id: Mapped[str] = mapped_column(String(36), ForeignKey("prompts.id"), nullable=False, index=True)
    depends_on_prompt_id: Mapped[str] = mapped_column(String(36), ForeignKey("prompts.id"), nullable=False, index=True)
    relationship_type: Mapped[str] = mapped_column(String(20), default=DependencyRelationship.REFERENCE.value, nullable=False)


class PromptHistoryModel(Base, IdMixin):
    """Append-only change log — distinct from the governance audit log:
    this is prompt-domain-scoped ("what changed on this prompt") vs. the
    audit log's platform-wide security/compliance scope."""

    __tablename__ = "prompt_history"

    prompt_id: Mapped[str] = mapped_column(String(36), ForeignKey("prompts.id"), nullable=False, index=True)
    version_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("prompt_versions.id"), nullable=True)
    actor_id: Mapped[str] = mapped_column(String(36), nullable=False)
    action: Mapped[str] = mapped_column(String(60), nullable=False)
    before: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    after: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    created_at = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)


class PromptReleaseModel(Base, IdMixin, AuditMixin):
    __tablename__ = "prompt_releases"

    prompt_id: Mapped[str] = mapped_column(String(36), ForeignKey("prompts.id"), nullable=False, index=True)
    version_id: Mapped[str] = mapped_column(String(36), ForeignKey("prompt_versions.id"), nullable=False, index=True)
    environment: Mapped[str] = mapped_column(String(20), nullable=False)
    release_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    released_by: Mapped[str] = mapped_column(String(36), nullable=False)
    released_at = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
