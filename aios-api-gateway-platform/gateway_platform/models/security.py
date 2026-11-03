"""Gateway Security schema: a generic policy table (`ip_filter`,
`geo_restriction`, `rate_limit`, `request_signing`, `bot_detection`,
`threat_detection` — the six policy types the prompt specifies) plus
two focused rule tables for the two policy types that need
structured, queryable rules (CIDR-based IP rules, country-code geo
rules) rather than a free-form config blob, and an append-only
security events feed for anything a policy or detector fires."""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import JSON, DateTime, String
from sqlalchemy.orm import Mapped, mapped_column

from gateway_platform.database.base import AuditMixin, Base, IdMixin, SoftDeleteMixin, utcnow


class GatewaySecurityPolicyModel(IdMixin, AuditMixin, SoftDeleteMixin, Base):
    __tablename__ = "gw_security_policies"

    tenant_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    policy_type: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(15), nullable=False, default="active", index=True)
    rules: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)


class IpRuleModel(IdMixin, Base):
    __tablename__ = "gw_ip_rules"

    tenant_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    policy_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    cidr: Mapped[str] = mapped_column(String(64), nullable=False)
    action: Mapped[str] = mapped_column(String(10), nullable=False, default="deny")


class GeoRuleModel(IdMixin, Base):
    __tablename__ = "gw_geo_rules"

    tenant_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    policy_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    country_code: Mapped[str] = mapped_column(String(2), nullable=False)
    action: Mapped[str] = mapped_column(String(10), nullable=False, default="deny")


class SecurityEventModel(IdMixin, Base):
    __tablename__ = "gw_security_events"

    tenant_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    event_type: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    source_ip: Mapped[str | None] = mapped_column(String(64), nullable=True)
    severity: Mapped[str] = mapped_column(String(10), nullable=False, default="info", index=True)
    details: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False, index=True)
