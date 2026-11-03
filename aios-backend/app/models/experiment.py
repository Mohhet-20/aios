from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import AuditMixin, Base, IdMixin, SoftDeleteMixin


class ExperimentModel(IdMixin, AuditMixin, SoftDeleteMixin, Base):
    __tablename__ = "experiments"

    workspace_id: Mapped[str] = mapped_column(String(36), index=True, nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    hypothesis: Mapped[str] = mapped_column(String(1000), default="", nullable=False)
    variant: Mapped[str] = mapped_column(String(255), default="", nullable=False)
    result_metric: Mapped[str] = mapped_column(String(255), default="", nullable=False)
    status: Mapped[str] = mapped_column(String(32), default="draft", nullable=False)
