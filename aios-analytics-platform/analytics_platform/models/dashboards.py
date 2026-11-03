"""Visualization & Dashboard Platform schema: a dashboard (guarded
draft -> published <-> archived), its widgets (one row per widget,
free-form `query_config` JSON so any of the eleven visualization types
the prompt specifies can be described without a dedicated table each),
and saved views (a named filter/layout preset a user can return to)."""
from __future__ import annotations

from sqlalchemy import JSON, String
from sqlalchemy.orm import Mapped, mapped_column

from analytics_platform.database.base import AuditMixin, Base, IdMixin, SoftDeleteMixin


class DashboardModel(IdMixin, AuditMixin, SoftDeleteMixin, Base):
    __tablename__ = "an_dashboards"

    tenant_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    owner_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    visibility: Mapped[str] = mapped_column(String(15), nullable=False, default="private")
    status: Mapped[str] = mapped_column(String(15), nullable=False, default="draft", index=True)
    layout: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)


class DashboardWidgetModel(IdMixin, AuditMixin, Base):
    __tablename__ = "an_dashboard_widgets"

    tenant_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    dashboard_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    visualization_type: Mapped[str] = mapped_column(String(20), nullable=False)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    query_config: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    position: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)


class SavedViewModel(IdMixin, AuditMixin, Base):
    __tablename__ = "an_saved_views"

    tenant_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    dashboard_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    owner_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    filters: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
