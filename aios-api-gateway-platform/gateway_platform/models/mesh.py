"""Service Mesh schema: a service registry (`gw_services`) with one
row per logical service and many `gw_service_instances` rows per
service (the actual routable endpoints), a load balancer pool
configuration per service, a circuit breaker per service tracking
closed -> open -> half_open state, and health check results feeding
both the circuit breaker and the instance's own health status."""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import JSON, Boolean, DateTime, Float, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from gateway_platform.database.base import AuditMixin, Base, IdMixin, SoftDeleteMixin, utcnow


class ServiceRegistrationModel(IdMixin, AuditMixin, SoftDeleteMixin, Base):
    __tablename__ = "gw_services"

    tenant_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(120), nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(15), nullable=False, default="registered", index=True)
    service_metadata: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)


class ServiceInstanceModel(IdMixin, AuditMixin, SoftDeleteMixin, Base):
    __tablename__ = "gw_service_instances"

    tenant_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    service_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    host: Mapped[str] = mapped_column(String(255), nullable=False)
    port: Mapped[int] = mapped_column(Integer, nullable=False, default=80)
    status: Mapped[str] = mapped_column(String(15), nullable=False, default="active", index=True)
    weight: Mapped[int] = mapped_column(Integer, nullable=False, default=1)


class LoadBalancerPoolModel(IdMixin, AuditMixin, Base):
    __tablename__ = "gw_load_balancer_pools"

    tenant_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    service_id: Mapped[str] = mapped_column(String(36), nullable=False, unique=True, index=True)
    strategy: Mapped[str] = mapped_column(String(30), nullable=False, default="round_robin")
    last_index: Mapped[int] = mapped_column(Integer, nullable=False, default=0)


class CircuitBreakerModel(IdMixin, AuditMixin, Base):
    __tablename__ = "gw_circuit_breakers"

    tenant_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    service_id: Mapped[str] = mapped_column(String(36), nullable=False, unique=True, index=True)
    state: Mapped[str] = mapped_column(String(15), nullable=False, default="closed", index=True)
    failure_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    failure_threshold: Mapped[int] = mapped_column(Integer, nullable=False, default=5)
    opened_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    half_opened_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class HealthCheckResultModel(IdMixin, Base):
    __tablename__ = "gw_health_check_results"

    tenant_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    instance_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    healthy: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    latency_ms: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    checked_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False, index=True)
