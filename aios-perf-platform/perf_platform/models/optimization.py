"""Auto-optimization recommendation engine's output: proposed changes
with a guarded editorial-decision lifecycle (see domain/entities.py)."""
from __future__ import annotations

from sqlalchemy import Float, String
from sqlalchemy.orm import Mapped, mapped_column

from perf_platform.database.base import AuditMixin, Base, IdMixin, SoftDeleteMixin
from perf_platform.domain.enums import RecommendationStatus


class RecommendationModel(IdMixin, AuditMixin, SoftDeleteMixin, Base):
    __tablename__ = "perf_recommendations"

    tenant_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    category: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str] = mapped_column(String, nullable=False, default="")
    target_ref: Mapped[str | None] = mapped_column(String(255), nullable=True)
    estimated_savings_usd: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    status: Mapped[str] = mapped_column(String(16), nullable=False, default=RecommendationStatus.PROPOSED.value, index=True)
