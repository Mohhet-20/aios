"""Recommendation Engine schema: one row per generated recommendation
across the eight optimization categories the prompt specifies, guarded
open -> accepted/dismissed -> implemented, carrying the evidence that
produced it so a reviewer can see why it was surfaced."""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import JSON, DateTime, String
from sqlalchemy.orm import Mapped, mapped_column

from analytics_platform.database.base import AuditMixin, Base, IdMixin, SoftDeleteMixin, utcnow


class RecommendationModel(IdMixin, AuditMixin, SoftDeleteMixin, Base):
    __tablename__ = "an_recommendations"

    tenant_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    category: Mapped[str] = mapped_column(String(30), nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str] = mapped_column(String(2000), nullable=False, default="")
    impact: Mapped[str] = mapped_column(String(10), nullable=False, default="medium")
    status: Mapped[str] = mapped_column(String(15), nullable=False, default="open", index=True)
    evidence: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    generated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
