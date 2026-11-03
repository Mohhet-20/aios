from sqlalchemy import Float, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import AuditMixin, Base, IdMixin


class EvaluationRunModel(IdMixin, AuditMixin, Base):
    __tablename__ = "evaluation_runs"

    workspace_id: Mapped[str] = mapped_column(String(36), index=True, nullable=False)
    suite_name: Mapped[str] = mapped_column(String(255), nullable=False)
    target_type: Mapped[str] = mapped_column(String(32), nullable=False)
    target_id: Mapped[str] = mapped_column(String(36), nullable=False)
    dataset_id: Mapped[str] = mapped_column(String(36), nullable=False)
    status: Mapped[str] = mapped_column(String(32), default="queued", nullable=False)
    total: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    passed: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    failed: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    score: Mapped[float | None] = mapped_column(Float, nullable=True)
    previous_score: Mapped[float | None] = mapped_column(Float, nullable=True)
