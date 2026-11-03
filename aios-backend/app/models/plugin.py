from sqlalchemy import Boolean, String
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import AuditMixin, Base, IdMixin


class PluginModel(IdMixin, AuditMixin, Base):
    __tablename__ = "plugins"

    organization_id: Mapped[str] = mapped_column(String(36), index=True, nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    category: Mapped[str] = mapped_column(String(64), default="", nullable=False)
    version: Mapped[str] = mapped_column(String(32), default="0.1.0", nullable=False)
    enabled: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)


class ToolModel(IdMixin, AuditMixin, Base):
    """The Tool Engine's registry (Phase 1, Section 3.6). Separate from
    `PluginModel` because a plugin can bundle multiple tools, and tools are
    referenced directly by `AgentModel.allowed_tool_ids`."""

    __tablename__ = "tools"

    organization_id: Mapped[str] = mapped_column(String(36), index=True, nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str] = mapped_column(String(1000), default="", nullable=False)
    category: Mapped[str] = mapped_column(String(64), default="", nullable=False)
    side_effect: Mapped[str] = mapped_column(String(16), default="read_only", nullable=False)
    verified: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    installs: Mapped[int] = mapped_column(default=0, nullable=False)
