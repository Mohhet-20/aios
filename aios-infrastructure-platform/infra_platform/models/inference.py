"""Inference Platform schema: inference services (real-time/batch/
streaming/async, on CPU or GPU compute, multi-model-capable) and the
routing rules that split traffic across variants of a service (used
by canary/blue-green deployments and multi-model serving alike)."""
from __future__ import annotations

from sqlalchemy import Boolean, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from infra_platform.database.base import AuditMixin, Base, IdMixin, SoftDeleteMixin


class InferenceServiceModel(IdMixin, AuditMixin, SoftDeleteMixin, Base):
    __tablename__ = "infra_inference_services"

    tenant_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    model_version_id: Mapped[str | None] = mapped_column(String(36), nullable=True, index=True)
    mode: Mapped[str] = mapped_column(String(15), nullable=False, default="real_time")
    compute_type: Mapped[str] = mapped_column(String(10), nullable=False, default="cpu")
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="provisioning", index=True)
    replicas: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    endpoint_url: Mapped[str | None] = mapped_column(String(500), nullable=True)


class InferenceRouteModel(IdMixin, AuditMixin, Base):
    __tablename__ = "infra_inference_routes"

    tenant_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    inference_service_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    path: Mapped[str] = mapped_column(String(300), nullable=False)
    weight: Mapped[int] = mapped_column(Integer, nullable=False, default=100)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
