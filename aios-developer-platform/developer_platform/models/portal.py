"""Developer Portal & Sandbox schema: portal content (getting
started, docs, tutorials, quickstarts, release notes, migration
guides) with a draft -> published -> archived lifecycle, and
provisioned sandbox environments (guarded provisioning -> running ->
expired/terminated) that let a developer try the platform without
touching production tenant data."""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from developer_platform.database.base import AuditMixin, Base, IdMixin, utcnow


class PortalContentModel(IdMixin, AuditMixin, Base):
    __tablename__ = "dev_portal_content"

    tenant_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    content_type: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    slug: Mapped[str] = mapped_column(String(200), nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(300), nullable=False)
    body: Mapped[str] = mapped_column(Text, nullable=False, default="")
    status: Mapped[str] = mapped_column(String(15), nullable=False, default="draft", index=True)
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)


class SandboxEnvironmentModel(IdMixin, Base):
    __tablename__ = "dev_sandbox_environments"

    tenant_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    developer_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(15), nullable=False, default="provisioning", index=True)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    terminated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
