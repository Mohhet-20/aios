"""Integration Hub schema: a connector catalog (one row per supported
enterprise system type — CRM, ERP, GitHub, Slack, etc. — with a JSON
config schema describing what a connection to it needs) and the
actual per-tenant connection instances. Consistent with this
platform's "own the pointer, not the data" posture, `credentials_ref`
is always an opaque reference, never a raw credential."""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import JSON, DateTime, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from gateway_platform.database.base import AuditMixin, Base, IdMixin, SoftDeleteMixin


class ConnectorModel(IdMixin, AuditMixin, SoftDeleteMixin, Base):
    __tablename__ = "gw_connectors"

    tenant_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    connector_type: Mapped[str] = mapped_column(String(30), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    config_schema: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    sync_interval_minutes: Mapped[int] = mapped_column(Integer, nullable=False, default=15)


class IntegrationConnectionModel(IdMixin, AuditMixin, SoftDeleteMixin, Base):
    __tablename__ = "gw_integration_connections"

    tenant_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    connector_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    status: Mapped[str] = mapped_column(String(15), nullable=False, default="pending", index=True)
    credentials_ref: Mapped[str | None] = mapped_column(String(255), nullable=True)
    config: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    last_sync_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
