"""The component registry — every other module (health, alerts,
incidents, topology) references a component by id, so it's the one
shared "what is being observed" table."""
from __future__ import annotations


from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column

from observability_platform.database.base import AuditMixin, Base, IdMixin, SoftDeleteMixin


class ComponentModel(IdMixin, AuditMixin, SoftDeleteMixin, Base):
    __tablename__ = "obs_components"

    tenant_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    component_type: Mapped[str] = mapped_column(String(30), nullable=False)
    description: Mapped[str | None] = mapped_column(String(2000), nullable=True)
    owner_team: Mapped[str | None] = mapped_column(String(200), nullable=True)
