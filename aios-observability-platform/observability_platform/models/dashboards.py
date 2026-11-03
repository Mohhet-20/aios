"""Dashboard definitions. A dashboard stores layout/widget
*configuration* only — no cached widget data. Every widget's actual
numbers are computed on demand at render time by
`dashboards/dashboard_service.py` calling straight into the metrics,
health, alerts, incidents, and capacity services, so a dashboard can
never show stale data."""
from __future__ import annotations

from sqlalchemy import JSON, Boolean, String
from sqlalchemy.orm import Mapped, mapped_column

from observability_platform.database.base import AuditMixin, Base, IdMixin, SoftDeleteMixin


class DashboardModel(IdMixin, AuditMixin, SoftDeleteMixin, Base):
    __tablename__ = "obs_dashboards"

    tenant_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    dashboard_type: Mapped[str] = mapped_column(String(30), nullable=False)
    owner: Mapped[str | None] = mapped_column(String(64), nullable=True)
    layout: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    widgets: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    is_default: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
