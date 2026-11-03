"""Environment Management schema: the 8 declared environment types
(dev, testing, QA, staging, production, sandbox, customer preview,
enterprise dedicated) a deployment or rollout can target."""
from __future__ import annotations

from sqlalchemy import Boolean, String
from sqlalchemy.orm import Mapped, mapped_column

from release_platform.database.base import AuditMixin, Base, IdMixin


class EnvironmentModel(IdMixin, AuditMixin, Base):
    __tablename__ = "rel_environments"

    tenant_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(120), nullable=False, index=True)
    environment_type: Mapped[str] = mapped_column(String(25), nullable=False, index=True)
    region: Mapped[str | None] = mapped_column(String(50), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
