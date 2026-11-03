"""AgentTypeModel: the data-driven registry of specialized agent roles.
This is what makes "add a new agent type without modifying existing
code" literally true — a new specialist is an INSERT, not a subclass.
The 17 spec'd types (Planner, Research, Reasoning, Critic, Reviewer,
Verifier, Coding, Documentation, Summarization, Retrieval, Memory, Tool,
Workflow, Reporting, Coordinator, Human Approval, System) are seeded as
rows via agent_registry/seed_types.py, not hardcoded classes.
"""
from __future__ import annotations

from sqlalchemy import JSON, Boolean, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from agent_platform.database.base import AuditMixin, Base, IdMixin
from agent_platform.domain.enums import AgentCategory


class AgentTypeModel(Base, IdMixin, AuditMixin):
    __tablename__ = "agent_types"

    key: Mapped[str] = mapped_column(String(60), nullable=False, unique=True, index=True)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    category: Mapped[str] = mapped_column(String(30), default=AgentCategory.CUSTOM.value, nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    default_instructions: Mapped[str] = mapped_column(Text, nullable=False)
    default_capabilities: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
    default_skills: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
    default_tool_names: Mapped[list] = mapped_column(JSON, default=list, nullable=False, doc="Tool names this type is granted by default")
    default_resource_limits: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    is_builtin: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
