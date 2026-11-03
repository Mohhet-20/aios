"""Learning Platform schema: tutorials across the four types the
prompt specifies, ordered learning paths, and role-based enrollment
tracking (against either a single tutorial or a full learning path)."""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import JSON, DateTime, Float, String
from sqlalchemy.orm import Mapped, mapped_column

from docs_platform.database.base import AuditMixin, Base, IdMixin, SoftDeleteMixin


class TutorialModel(IdMixin, AuditMixin, SoftDeleteMixin, Base):
    __tablename__ = "doc_tutorials"

    tenant_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    tutorial_type: Mapped[str] = mapped_column(String(25), nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(300), nullable=False)
    role: Mapped[str] = mapped_column(String(25), nullable=False, index=True)
    steps: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    pass_threshold_pct: Mapped[float] = mapped_column(Float, nullable=False, default=80.0)


class LearningPathModel(IdMixin, AuditMixin, SoftDeleteMixin, Base):
    __tablename__ = "doc_learning_paths"

    tenant_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    role: Mapped[str] = mapped_column(String(25), nullable=False, index=True)
    tutorial_ids: Mapped[list] = mapped_column(JSON, nullable=False, default=list)


class EnrollmentModel(IdMixin, AuditMixin, Base):
    __tablename__ = "doc_enrollments"

    tenant_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    user_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    tutorial_id: Mapped[str | None] = mapped_column(String(36), nullable=True, index=True)
    learning_path_id: Mapped[str | None] = mapped_column(String(36), nullable=True, index=True)
    status: Mapped[str] = mapped_column(String(15), nullable=False, default="enrolled", index=True)
    progress_pct: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
