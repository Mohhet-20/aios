from sqlalchemy import Float, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import AuditMixin, Base, IdMixin, SoftDeleteMixin, VersionedMixin


class AgentModel(IdMixin, AuditMixin, SoftDeleteMixin, VersionedMixin, Base):
    __tablename__ = "agents"

    workspace_id: Mapped[str] = mapped_column(String(36), index=True, nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str] = mapped_column(String(1000), default="", nullable=False)
    model_id: Mapped[str] = mapped_column(String(64), nullable=False)
    allowed_tool_ids: Mapped[str] = mapped_column(String(1000), default="", nullable=False)  # comma-separated
    status: Mapped[str] = mapped_column(String(32), default="idle", nullable=False)
    runs_today: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    success_rate: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
