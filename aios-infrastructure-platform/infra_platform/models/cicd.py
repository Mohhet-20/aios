"""CI/CD schema: pipelines (definitions), runs (one per trigger),
per-stage run records (build/test/static-analysis/security-scan/
publish/deploy), deployment gates (manual or policy approval points
within a run), and releases (promotion/rollback tracking)."""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import JSON, Boolean, DateTime, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from infra_platform.database.base import AuditMixin, Base, IdMixin, SoftDeleteMixin, VersionedMixin, utcnow


class PipelineModel(IdMixin, AuditMixin, SoftDeleteMixin, Base):
    __tablename__ = "infra_pipelines"

    tenant_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    repository: Mapped[str] = mapped_column(String(300), nullable=False)
    default_branch: Mapped[str] = mapped_column(String(100), nullable=False, default="main")
    stages: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    is_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)


class PipelineRunModel(IdMixin, AuditMixin, Base):
    __tablename__ = "infra_pipeline_runs"

    tenant_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    pipeline_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    commit_sha: Mapped[str] = mapped_column(String(64), nullable=False)
    branch: Mapped[str] = mapped_column(String(100), nullable=False, default="main")
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="pending", index=True)
    triggered_by: Mapped[str | None] = mapped_column(String(64), nullable=True)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class PipelineStageRunModel(IdMixin, Base):
    __tablename__ = "infra_pipeline_stage_runs"

    tenant_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    run_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    stage_type: Mapped[str] = mapped_column(String(20), nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="pending")
    logs_excerpt: Mapped[str] = mapped_column(String(4000), nullable=False, default="")
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class DeploymentGateModel(IdMixin, AuditMixin, Base):
    __tablename__ = "infra_deployment_gates"

    tenant_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    pipeline_run_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="pending")
    required_approvals: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    approvals_received: Mapped[int] = mapped_column(Integer, nullable=False, default=0)


class ReleaseModel(IdMixin, AuditMixin, VersionedMixin, Base):
    __tablename__ = "infra_releases"

    tenant_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    version: Mapped[str] = mapped_column(String(50), nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="draft", index=True)
    pipeline_run_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    released_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    rolled_back_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
