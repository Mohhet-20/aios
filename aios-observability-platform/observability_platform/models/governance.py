"""Security & governance: access grants (a small ordered role, see
`ObservabilityRole` — deliberately simpler than the Identity Platform's
fine-grained RBAC, since this platform only needs viewer/operator/admin
over telemetry), an immutable audit log distinct from any product
activity feed, and per-tenant/per-resource-type retention policies."""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import JSON, Boolean, DateTime, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from observability_platform.database.base import AuditMixin, Base, IdMixin, SoftDeleteMixin, utcnow


class AccessGrantModel(IdMixin, AuditMixin, SoftDeleteMixin, Base):
    __tablename__ = "obs_access_grants"

    tenant_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    principal_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    role: Mapped[str] = mapped_column(String(20), nullable=False, default="viewer")
    component_id: Mapped[str | None] = mapped_column(String(36), nullable=True, index=True)


class AuditLogEntryModel(IdMixin, Base):
    __tablename__ = "obs_audit_log_entries"

    tenant_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    actor_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    action: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    resource_type: Mapped[str] = mapped_column(String(50), nullable=False)
    resource_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    details: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False, index=True)


class RetentionPolicyModel(IdMixin, AuditMixin, Base):
    __tablename__ = "obs_retention_policies"

    tenant_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    resource_type: Mapped[str] = mapped_column(String(50), nullable=False)
    retention_days: Mapped[int] = mapped_column(Integer, nullable=False, default=30)
    is_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
