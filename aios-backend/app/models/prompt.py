from sqlalchemy import Float, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import AuditMixin, Base, IdMixin, SoftDeleteMixin


class PromptModel(IdMixin, AuditMixin, SoftDeleteMixin, Base):
    __tablename__ = "prompts"

    workspace_id: Mapped[str] = mapped_column(String(36), index=True, nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str] = mapped_column(String(1000), default="", nullable=False)
    target_model: Mapped[str] = mapped_column(String(64), nullable=False)
    tags: Mapped[str] = mapped_column(String(500), default="", nullable=False)  # comma-separated


class PromptVersionModel(IdMixin, AuditMixin, Base):
    __tablename__ = "prompt_versions"

    prompt_id: Mapped[str] = mapped_column(String(36), index=True, nullable=False)
    version: Mapped[int] = mapped_column(Integer, nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String(32), default="draft", nullable=False)
    author_id: Mapped[str] = mapped_column(String(36), nullable=False)
    eval_score: Mapped[float | None] = mapped_column(Float, nullable=True)
