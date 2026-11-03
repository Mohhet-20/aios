"""GPU pool inventory — supports GPU scheduling/sharing/autoscaling
architecture without this platform itself owning real GPU hardware."""
from __future__ import annotations

from sqlalchemy import Boolean, Float, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from perf_platform.database.base import AuditMixin, Base, IdMixin, SoftDeleteMixin


class GpuPoolModel(IdMixin, AuditMixin, SoftDeleteMixin, Base):
    __tablename__ = "perf_gpu_pools"

    tenant_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    pool_type: Mapped[str] = mapped_column(String(32), nullable=False)
    gpu_count: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    utilization_pct: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
