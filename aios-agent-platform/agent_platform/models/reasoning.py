"""Reasoning traces (chain-of-thought / tree-of-thought step logs) and
reflection/critique cycle records — the "show your work" and
"did you check your work" halves of the Reasoning & Reflection engine."""
from __future__ import annotations

from sqlalchemy import JSON, Boolean, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from agent_platform.database.base import Base, IdMixin, utcnow
from agent_platform.domain.enums import ReasoningMode


class ReasoningTraceModel(Base, IdMixin):
    __tablename__ = "agent_reasoning_traces"

    execution_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("agent_executions.id"), nullable=True, index=True)
    task_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("agent_tasks.id"), nullable=True, index=True)
    agent_id: Mapped[str] = mapped_column(String(36), ForeignKey("agents.id"), nullable=False, index=True)

    mode: Mapped[str] = mapped_column(String(20), default=ReasoningMode.CHAIN_OF_THOUGHT.value, nullable=False)
    steps: Mapped[list] = mapped_column(JSON, default=list, nullable=False, doc="[{step, thought, action, observation}]")
    branches_explored: Mapped[int] = mapped_column(Integer, default=1, nullable=False, doc="1 for chain-of-thought; >1 for tree-of-thought")
    final_answer: Mapped[str | None] = mapped_column(Text, nullable=True)
    confidence: Mapped[float | None] = mapped_column(Float, nullable=True)

    created_at = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)


class ReflectionModel(Base, IdMixin):
    __tablename__ = "agent_reflections"

    execution_id: Mapped[str] = mapped_column(String(36), ForeignKey("agent_executions.id"), nullable=False, index=True)
    task_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("agent_tasks.id"), nullable=True, index=True)
    reflecting_agent_id: Mapped[str] = mapped_column(String(36), ForeignKey("agents.id"), nullable=False, doc="The critic/reviewer/verifier doing the reflecting")

    iteration: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    critique: Mapped[str] = mapped_column(Text, nullable=False)
    self_correction: Mapped[str | None] = mapped_column(Text, nullable=True)
    passed_verification: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    confidence: Mapped[float | None] = mapped_column(Float, nullable=True)

    created_at = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
