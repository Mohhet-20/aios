"""Explicit, auditable tool-permission grants per agent — kept as a real
table (not a JSON blob on AgentModel) because governance needs to list,
revoke, and audit these independently of the agent's own edit history."""
from __future__ import annotations

from sqlalchemy import DateTime, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from agent_platform.database.base import Base, IdMixin, utcnow
from agent_platform.domain.enums import ToolPermissionLevel


class AgentToolPermissionModel(Base, IdMixin):
    __tablename__ = "agent_tool_permissions"

    agent_id: Mapped[str] = mapped_column(String(36), ForeignKey("agents.id"), nullable=False, index=True)
    tool_name: Mapped[str] = mapped_column(String(120), nullable=False)
    permission_level: Mapped[str] = mapped_column(String(20), default=ToolPermissionLevel.EXECUTE.value, nullable=False)
    granted_by: Mapped[str] = mapped_column(String(36), nullable=False)
    granted_at = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
