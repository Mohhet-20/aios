"""SecurityPolicyModel: a data-driven, org-scoped (or platform-default
when `organization_id` is null) security rule — password requirements,
session limits, IP/geo restriction lists, MFA-required-for-role, all as
`config` JSON rather than one table per policy type, the same pattern
`AlertRuleModel.condition` uses in the Evaluation Platform.
`SecurityEventModel` is the record an anomaly/brute-force/lockout/
suspicious-login detection produces — genuinely triggered by a real
signal, never a synthetic entry."""
from __future__ import annotations

from sqlalchemy import JSON, Boolean, DateTime, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from identity_platform.database.base import Base, IdMixin, utcnow


class SecurityPolicyModel(Base, IdMixin):
    __tablename__ = "ip_security_policies"

    organization_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("ip_organizations.id"), nullable=True, index=True)
    policy_type: Mapped[str] = mapped_column(String(30), nullable=False, index=True)
    config: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    updated_at = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow, nullable=False)


class SecurityEventModel(Base, IdMixin):
    __tablename__ = "ip_security_events"

    organization_id: Mapped[str | None] = mapped_column(String(36), nullable=True, index=True)
    user_id: Mapped[str | None] = mapped_column(String(36), nullable=True, index=True)
    event_type: Mapped[str] = mapped_column(String(30), nullable=False, index=True)
    severity: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    details: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    resolved: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
