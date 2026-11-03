"""Plugin SDK schema: a plugin (logical name), versions beneath it
carrying the manifest and a guarded draft -> validated -> signed ->
published -> deprecated lifecycle, a dependency graph between plugin
versions, and a marketplace listing with review status and install
metrics."""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import JSON, Boolean, DateTime, Float, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from developer_platform.database.base import AuditMixin, Base, IdMixin, SoftDeleteMixin


class PluginModel(IdMixin, AuditMixin, SoftDeleteMixin, Base):
    __tablename__ = "dev_plugins"

    tenant_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    category: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    owner_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    description: Mapped[str | None] = mapped_column(String(2000), nullable=True)
    homepage_url: Mapped[str | None] = mapped_column(String(500), nullable=True)


class PluginVersionModel(IdMixin, AuditMixin, Base):
    __tablename__ = "dev_plugin_versions"

    tenant_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    plugin_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    version: Mapped[str] = mapped_column(String(50), nullable=False)
    manifest: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    status: Mapped[str] = mapped_column(String(15), nullable=False, default="draft", index=True)
    signature: Mapped[str | None] = mapped_column(String(500), nullable=True)
    signed_by: Mapped[str | None] = mapped_column(String(64), nullable=True)
    validation_errors: Mapped[list] = mapped_column(JSON, nullable=False, default=list)


class PluginDependencyModel(IdMixin, Base):
    __tablename__ = "dev_plugin_dependencies"

    tenant_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    plugin_version_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    depends_on_plugin_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    version_constraint: Mapped[str] = mapped_column(String(50), nullable=False, default="*")


class PluginMarketplaceListingModel(IdMixin, AuditMixin, Base):
    __tablename__ = "dev_plugin_marketplace_listings"

    tenant_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    plugin_id: Mapped[str] = mapped_column(String(36), nullable=False, unique=True, index=True)
    is_listed: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    review_status: Mapped[str] = mapped_column(String(15), nullable=False, default="pending", index=True)
    reviewer_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    install_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    rating_avg: Mapped[float | None] = mapped_column(Float, nullable=True)
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
