"""PluginModel: a marketplace-listed extension package (the thing you'd
browse in the Plugin Marketplace) — versioned, signed, with declared
dependencies. `PluginInstallationModel` is a specific workspace's copy
of it, which is what actually gets enabled/disabled/configured; the same
split as Tool/ToolVersion, for the same reason (a workspace's installed
copy shouldn't shift under it when the marketplace listing updates)."""
from __future__ import annotations

from sqlalchemy import JSON, Boolean, DateTime, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from tool_platform.database.base import AuditMixin, Base, IdMixin, SoftDeleteMixin, utcnow
from tool_platform.domain.enums import PluginInstallationStatus, PluginStatus


class PluginModel(Base, IdMixin, AuditMixin, SoftDeleteMixin):
    __tablename__ = "tp_plugins"

    name: Mapped[str] = mapped_column(String(200), nullable=False)
    slug: Mapped[str] = mapped_column(String(220), nullable=False, index=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    author: Mapped[str] = mapped_column(String(200), nullable=False)
    organization_id: Mapped[str | None] = mapped_column(String(36), nullable=True, index=True, doc="Publisher org; null for platform-provided plugins")
    category: Mapped[str] = mapped_column(String(40), nullable=False, index=True)
    tags: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
    latest_version: Mapped[str] = mapped_column(String(40), nullable=False, default="0.1.0")
    status: Mapped[str] = mapped_column(String(20), default=PluginStatus.DRAFT.value, nullable=False, index=True)
    is_signed: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    signature: Mapped[str | None] = mapped_column(Text, nullable=True)
    checksum: Mapped[str | None] = mapped_column(String(128), nullable=True)
    manifest: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False, doc="Declared tools/capabilities/entry points this plugin provides")
    install_count: Mapped[int] = mapped_column(default=0, nullable=False)


class PluginDependencyModel(Base, IdMixin):
    __tablename__ = "tp_plugin_dependencies"

    plugin_id: Mapped[str] = mapped_column(String(36), ForeignKey("tp_plugins.id"), nullable=False, index=True)
    depends_on_plugin_id: Mapped[str] = mapped_column(String(36), ForeignKey("tp_plugins.id"), nullable=False, index=True)
    version_constraint: Mapped[str] = mapped_column(String(80), nullable=False, default="*")


class PluginInstallationModel(Base, IdMixin, AuditMixin):
    __tablename__ = "tp_plugin_installations"

    plugin_id: Mapped[str] = mapped_column(String(36), ForeignKey("tp_plugins.id"), nullable=False, index=True)
    workspace_id: Mapped[str] = mapped_column(String(36), ForeignKey("tp_workspaces.id"), nullable=False, index=True)
    installed_version: Mapped[str] = mapped_column(String(40), nullable=False)
    status: Mapped[str] = mapped_column(String(20), default=PluginInstallationStatus.INSTALLED.value, nullable=False, index=True)
    configuration: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    installed_by: Mapped[str] = mapped_column(String(36), nullable=False)
    installed_at = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    last_verified_at: Mapped[object | None] = mapped_column(DateTime(timezone=True), nullable=True)
