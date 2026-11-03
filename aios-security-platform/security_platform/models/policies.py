"""Policy engine schema. `PolicyModel.parent_policy_id` supports
inheritance (a policy can be a specialization of a broader-scope
policy); `PolicyVersionModel` is an immutable snapshot taken on every
edit so policy history is never lost; `PolicyExceptionModel` is a
time-boxed carve-out for a specific resource within a policy's scope."""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import JSON, DateTime, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from security_platform.database.base import AuditMixin, Base, IdMixin, SoftDeleteMixin, VersionedMixin, utcnow


class PolicyModel(IdMixin, AuditMixin, SoftDeleteMixin, VersionedMixin, Base):
    __tablename__ = "sec_policies"

    tenant_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str | None] = mapped_column(String(2000), nullable=True)
    scope: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    scope_ref_id: Mapped[str | None] = mapped_column(String(36), nullable=True, index=True)
    parent_policy_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    effect: Mapped[str] = mapped_column(String(10), nullable=False, default="deny")
    rules: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="draft")
    priority: Mapped[int] = mapped_column(Integer, nullable=False, default=100)


class PolicyVersionModel(IdMixin, Base):
    __tablename__ = "sec_policy_versions"

    tenant_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    policy_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    version_number: Mapped[int] = mapped_column(Integer, nullable=False)
    rules_snapshot: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    effect_snapshot: Mapped[str] = mapped_column(String(10), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    created_by: Mapped[str | None] = mapped_column(String(36), nullable=True)


class PolicyExceptionModel(IdMixin, AuditMixin, SoftDeleteMixin, Base):
    __tablename__ = "sec_policy_exceptions"

    tenant_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    policy_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    scope_ref_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    reason: Mapped[str] = mapped_column(String(2000), nullable=False)
    granted_by: Mapped[str | None] = mapped_column(String(36), nullable=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
