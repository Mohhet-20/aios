"""DelegationModel: a task handed from one agent (or the system) to
another — the record of "who is doing this and did they accept it,"
which is what makes delegation chains inspectable after the fact."""
from __future__ import annotations

from sqlalchemy import JSON, DateTime, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from agent_platform.database.base import Base, IdMixin, utcnow
from agent_platform.domain.enums import DelegationStatus


class DelegationModel(Base, IdMixin):
    __tablename__ = "agent_delegations"

    task_id: Mapped[str] = mapped_column(String(36), ForeignKey("agent_tasks.id"), nullable=False, index=True)
    from_agent_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("agents.id"), nullable=True, doc="Null = system/coordinator-initiated")
    to_agent_id: Mapped[str] = mapped_column(String(36), ForeignKey("agents.id"), nullable=False, index=True)

    status: Mapped[str] = mapped_column(String(20), default=DelegationStatus.PROPOSED.value, nullable=False)
    reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    result: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    created_at = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    accepted_at = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at = mapped_column(DateTime(timezone=True), nullable=True)
