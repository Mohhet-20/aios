"""Deployments — prompts treated as deployable artifacts across
environments, with approval gating and rollback."""
from __future__ import annotations

from sqlalchemy import JSON, DateTime, Float, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from prompt_platform.database.base import AuditMixin, Base, IdMixin
from prompt_platform.domain.enums import DeploymentStatus


class DeploymentModel(Base, IdMixin, AuditMixin):
    __tablename__ = "deployments"

    prompt_id: Mapped[str] = mapped_column(String(36), ForeignKey("prompts.id"), nullable=False, index=True)
    version_id: Mapped[str] = mapped_column(String(36), ForeignKey("prompt_versions.id"), nullable=False, index=True)
    environment: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(20), default=DeploymentStatus.PENDING_APPROVAL.value, nullable=False)
    canary_percent: Mapped[float] = mapped_column(Float, default=100.0, nullable=False)
    requested_by: Mapped[str] = mapped_column(String(36), nullable=False)
    approved_by: Mapped[str | None] = mapped_column(String(36), nullable=True)
    approved_at = mapped_column(DateTime(timezone=True), nullable=True)
    deployed_at = mapped_column(DateTime(timezone=True), nullable=True)
    rollback_of_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("deployments.id"), nullable=True)
    notes: Mapped[str | None] = mapped_column(String(500), nullable=True)


class DeploymentEnvironmentConfigModel(Base, IdMixin, AuditMixin):
    __tablename__ = "deployment_environment_configs"

    workspace_id: Mapped[str] = mapped_column(String(36), ForeignKey("prompt_workspaces.id"), nullable=False, index=True)
    environment: Mapped[str] = mapped_column(String(20), nullable=False)
    variables: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False, doc="env-scoped config/variable overrides")
    updated_by: Mapped[str] = mapped_column(String(36), nullable=False)
