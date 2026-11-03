"""Extension Framework schema: an extension point registry — the
contract surface developers can plug into (agents, prompts,
workflows, memory, tools, models, evaluation, dashboards,
authentication, notifications, custom UI components) — and the
registrations bound to each point, optionally backed by a published
plugin version."""
from __future__ import annotations

from sqlalchemy import JSON, String
from sqlalchemy.orm import Mapped, mapped_column

from developer_platform.database.base import AuditMixin, Base, IdMixin


class ExtensionPointModel(IdMixin, AuditMixin, Base):
    __tablename__ = "dev_extension_points"

    tenant_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    category: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str | None] = mapped_column(String(2000), nullable=True)
    contract_schema: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)


class ExtensionRegistrationModel(IdMixin, AuditMixin, Base):
    __tablename__ = "dev_extension_registrations"

    tenant_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    extension_point_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    plugin_id: Mapped[str | None] = mapped_column(String(36), nullable=True, index=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    status: Mapped[str] = mapped_column(String(15), nullable=False, default="registered", index=True)
    config: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
