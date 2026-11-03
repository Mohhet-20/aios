from sqlalchemy import Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import AuditMixin, Base, IdMixin, SoftDeleteMixin


class DatasetModel(IdMixin, AuditMixin, SoftDeleteMixin, Base):
    __tablename__ = "datasets"

    workspace_id: Mapped[str] = mapped_column(String(36), index=True, nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    dataset_type: Mapped[str] = mapped_column(String(32), default="reference", nullable=False)
    row_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    used_by: Mapped[str] = mapped_column(String(255), default="", nullable=False)
