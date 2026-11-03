"""AgentModel: identity, role, capabilities, skills, goals, instructions,
memory access config, context window, configuration, version, lifecycle,
health status, and resource limits — every field the spec's AGENT
ARCHITECTURE section calls for. `agent_type_id` is what makes an agent
"a Planner" or "a Critic"; the agent row itself holds the
instance-specific overrides (its own instructions, goals, tool grants).
"""
from __future__ import annotations

from sqlalchemy import JSON, Boolean, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from agent_platform.database.base import AuditMixin, Base, IdMixin, SoftDeleteMixin, VersionedMixin
from agent_platform.domain.enums import AgentHealthStatus, AgentLifecycleStatus


class AgentModel(Base, IdMixin, AuditMixin, SoftDeleteMixin, VersionedMixin):
    __tablename__ = "agents"

    workspace_id: Mapped[str] = mapped_column(String(36), ForeignKey("agent_workspaces.id"), nullable=False, index=True)
    agent_type_id: Mapped[str] = mapped_column(String(36), ForeignKey("agent_types.id"), nullable=False, index=True)

    name: Mapped[str] = mapped_column(String(200), nullable=False)
    slug: Mapped[str] = mapped_column(String(220), nullable=False, index=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    owner_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)

    role: Mapped[str] = mapped_column(String(120), nullable=False, doc="Human-readable role, e.g. 'Senior Research Analyst'")
    goals: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
    instructions: Mapped[str] = mapped_column(Text, nullable=False, doc="System-prompt-equivalent instructions")
    capabilities: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
    skills: Mapped[list] = mapped_column(JSON, default=list, nullable=False)

    memory_access: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False, doc="{short_term: bool, long_term: bool, semantic: bool}")
    context_window_override: Mapped[int | None] = mapped_column(nullable=True)
    configuration: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False, doc="{model, provider, temperature, max_tokens, response_format}")
    resource_limits: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False, doc="{max_tokens_per_run, max_cost_per_run_usd, max_concurrent_tasks, timeout_seconds}")

    status: Mapped[str] = mapped_column(String(20), default=AgentLifecycleStatus.DRAFT.value, nullable=False)
    health_status: Mapped[str] = mapped_column(String(20), default=AgentHealthStatus.UNKNOWN.value, nullable=False)
    is_autonomous: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False, doc="False = every action needs human approval")

    prompt_version_id: Mapped[str | None] = mapped_column(
        String(36), nullable=True,
        doc="Optional forward-reference to a Prompt Platform PromptVersion id — loose coupling, no hard dependency on that project.",
    )
    tags: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
