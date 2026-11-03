"""Developer Analytics schema: a generic usage-event point shared by
every metric family this platform emits (SDK calls, API calls, CLI
commands, plugin installs, webhook deliveries, developer activity,
package downloads, API errors), distinguished by `event_type` /
`resource_type` / `metadata` rather than eight separate tables."""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import JSON, DateTime, String
from sqlalchemy.orm import Mapped, mapped_column

from developer_platform.database.base import Base, IdMixin, utcnow


class UsageEventModel(IdMixin, Base):
    __tablename__ = "dev_usage_events"

    tenant_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    event_type: Mapped[str] = mapped_column(String(30), nullable=False, index=True)
    resource_type: Mapped[str | None] = mapped_column(String(30), nullable=True, index=True)
    resource_id: Mapped[str | None] = mapped_column(String(36), nullable=True, index=True)
    developer_id: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    event_metadata: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    recorded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False, index=True)
