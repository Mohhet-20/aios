"""Model Lifecycle Management schema: a registry entry per logical
model name, versions beneath it (guarded lifecycle across
development -> staging -> production -> archived), approval records
gating promotion, and lightweight lineage edges (which dataset/run/
parent-version a version was produced from)."""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import JSON, DateTime, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from infra_platform.database.base import AuditMixin, Base, IdMixin, SoftDeleteMixin, utcnow


class ModelRegistryEntryModel(IdMixin, AuditMixin, SoftDeleteMixin, Base):
    __tablename__ = "infra_model_registry_entries"

    tenant_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str | None] = mapped_column(String(2000), nullable=True)
    owner_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    current_production_version_id: Mapped[str | None] = mapped_column(String(36), nullable=True)


class ModelVersionModel(IdMixin, AuditMixin, Base):
    __tablename__ = "infra_model_versions"

    tenant_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    model_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    version_number: Mapped[int] = mapped_column(Integer, nullable=False)
    stage: Mapped[str] = mapped_column(String(20), nullable=False, default="development", index=True)
    source_run_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    artifact_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    metrics: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    version_metadata: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)


class ModelApprovalModel(IdMixin, AuditMixin, Base):
    __tablename__ = "infra_model_approvals"

    tenant_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    model_version_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="pending")
    requested_stage: Mapped[str] = mapped_column(String(20), nullable=False)
    reviewer_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    decided_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    comments: Mapped[str | None] = mapped_column(String(2000), nullable=True)


class ModelLineageEdgeModel(IdMixin, Base):
    __tablename__ = "infra_model_lineage_edges"

    tenant_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    model_version_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    parent_type: Mapped[str] = mapped_column(String(30), nullable=False)
    parent_ref_id: Mapped[str] = mapped_column(String(36), nullable=False)
    recorded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
