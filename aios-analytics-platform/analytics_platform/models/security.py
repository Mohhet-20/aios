"""Security & Governance schema: a lightweight RBAC role-grant table,
row-level and column-level security rule tables, an append-only audit
log, and a data-lineage edge table (source -> transform -> aggregate
-> output) so any number on a dashboard can be traced back to the raw
events that produced it."""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import JSON, DateTime, String
from sqlalchemy.orm import Mapped, mapped_column

from analytics_platform.database.base import Base, IdMixin, utcnow


class AnalyticsRoleGrantModel(IdMixin, Base):
    __tablename__ = "an_role_grants"

    tenant_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    principal_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    role_level: Mapped[str] = mapped_column(String(10), nullable=False, default="viewer")
    scope: Mapped[str | None] = mapped_column(String(120), nullable=True)


class RowLevelSecurityRuleModel(IdMixin, Base):
    __tablename__ = "an_row_level_rules"

    tenant_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    resource_type: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    mode: Mapped[str] = mapped_column(String(20), nullable=False, default="tenant_scoped")
    rule_expression: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)


class ColumnLevelSecurityRuleModel(IdMixin, Base):
    __tablename__ = "an_column_level_rules"

    tenant_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    resource_type: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    restricted_columns: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    allowed_roles: Mapped[list] = mapped_column(JSON, nullable=False, default=list)


class AuditLogEntryModel(IdMixin, Base):
    __tablename__ = "an_audit_log"

    tenant_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    actor_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    action_type: Mapped[str] = mapped_column(String(10), nullable=False, index=True)
    resource_type: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    resource_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    details: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False, index=True)


class DataLineageEdgeModel(IdMixin, Base):
    __tablename__ = "an_data_lineage_edges"

    tenant_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    source_ref: Mapped[str] = mapped_column(String(200), nullable=False, index=True)
    target_ref: Mapped[str] = mapped_column(String(200), nullable=False, index=True)
    stage_type: Mapped[str] = mapped_column(String(15), nullable=False, default="transform")
    transform_description: Mapped[str | None] = mapped_column(String(500), nullable=True)
    recorded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
