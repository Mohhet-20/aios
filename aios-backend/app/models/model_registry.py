from sqlalchemy import Boolean, Float, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import AuditMixin, Base, IdMixin


class ModelRegistryEntry(IdMixin, AuditMixin, Base):
    """Represents one entry in the AI Core's model registry (Phase 1,
    Section 3.1). AIOS never calls a provider SDK directly from this table —
    it only records *which* models/providers are configured and their
    capabilities/pricing; the actual adapter implementation is
    `app.infrastructure.ai_providers`, explicitly stubbed per this phase's
    scope boundary."""

    __tablename__ = "model_registry"

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    provider: Mapped[str] = mapped_column(String(32), nullable=False)
    context_window: Mapped[int] = mapped_column(Integer, nullable=False)
    cost_per_1k_input: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    cost_per_1k_output: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    modality: Mapped[str] = mapped_column(String(64), default="text", nullable=False)  # comma-separated
    status: Mapped[str] = mapped_column(String(32), default="available", nullable=False)
    is_enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
