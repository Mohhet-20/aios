"""Inter-agent communication log: direct/broadcast/status/handoff/event/
stream-chunk/log messages all flow through one table so a conversation
or task's full communication history can be reconstructed in order."""
from __future__ import annotations

from sqlalchemy import JSON, DateTime, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from agent_platform.database.base import Base, IdMixin, utcnow
from agent_platform.domain.enums import MessageType


class MessageModel(Base, IdMixin):
    __tablename__ = "agent_messages"

    task_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("agent_tasks.id"), nullable=True, index=True)
    from_agent_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("agents.id"), nullable=True, doc="Null = system")
    to_agent_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("agents.id"), nullable=True, doc="Null = broadcast")

    message_type: Mapped[str] = mapped_column(String(20), default=MessageType.DIRECT.value, nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    structured_payload: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    created_at = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)


class SharedWorkspaceEntryModel(Base, IdMixin):
    """A simple key/value blackboard scoped per task — agents collaborating
    on the same task read/write shared state here instead of only
    exchanging point-to-point messages."""

    __tablename__ = "agent_shared_workspace_entries"

    task_id: Mapped[str] = mapped_column(String(36), ForeignKey("agent_tasks.id"), nullable=False, index=True)
    key: Mapped[str] = mapped_column(String(200), nullable=False)
    value: Mapped[dict] = mapped_column(JSON, nullable=False)
    updated_by: Mapped[str | None] = mapped_column(String(36), nullable=True)
    updated_at = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow, nullable=False)
