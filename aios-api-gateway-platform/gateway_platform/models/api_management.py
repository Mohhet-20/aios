"""API Management schema: key issuance (hashed at rest, `own the
pointer not the data`), usage records backing the sliding-window rate
limiter, the platform-wide API version lifecycle, OAuth-ready client
registration, and a request/response schema registry keyed to a
route."""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import JSON, DateTime, Float, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from gateway_platform.database.base import AuditMixin, Base, IdMixin, SoftDeleteMixin, utcnow


class ApiKeyModel(IdMixin, AuditMixin, SoftDeleteMixin, Base):
    __tablename__ = "gw_api_keys"

    tenant_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    key_hash: Mapped[str] = mapped_column(String(64), nullable=False, unique=True, index=True)
    key_prefix: Mapped[str] = mapped_column(String(16), nullable=False, index=True)
    scopes: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    rate_limit_per_minute: Mapped[int] = mapped_column(Integer, nullable=False, default=120)
    quota_per_day: Mapped[int] = mapped_column(Integer, nullable=False, default=100000)
    status: Mapped[str] = mapped_column(String(15), nullable=False, default="active", index=True)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class ApiUsageRecordModel(IdMixin, Base):
    __tablename__ = "gw_api_usage_records"

    tenant_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    api_key_id: Mapped[str | None] = mapped_column(String(36), nullable=True, index=True)
    route_id: Mapped[str | None] = mapped_column(String(36), nullable=True, index=True)
    endpoint: Mapped[str] = mapped_column(String(500), nullable=False)
    method: Mapped[str] = mapped_column(String(10), nullable=False)
    status_code: Mapped[int] = mapped_column(Integer, nullable=False, default=200)
    latency_ms: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    recorded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False, index=True)


class ApiVersionModel(IdMixin, Base):
    __tablename__ = "gw_api_versions"

    version: Mapped[str] = mapped_column(String(30), nullable=False, unique=True, index=True)
    status: Mapped[str] = mapped_column(String(15), nullable=False, default="active", index=True)
    notes: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    sunset_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)


class OAuthClientModel(IdMixin, AuditMixin, SoftDeleteMixin, Base):
    __tablename__ = "gw_oauth_clients"

    tenant_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    client_id: Mapped[str] = mapped_column(String(64), nullable=False, unique=True, index=True)
    client_secret_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    redirect_uris: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    scopes: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    status: Mapped[str] = mapped_column(String(15), nullable=False, default="active", index=True)


class ApiSchemaModel(IdMixin, AuditMixin, SoftDeleteMixin, Base):
    __tablename__ = "gw_api_schemas"

    tenant_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    route_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    schema_kind: Mapped[str] = mapped_column(String(10), nullable=False, default="request")
    json_schema: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
