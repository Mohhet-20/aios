"""ORM <-> domain-aggregate bridge for Agent, mirroring the Prompt
Platform's mappers.py pattern."""
from __future__ import annotations

from agent_platform.domain.entities import Agent
from agent_platform.domain.enums import AgentHealthStatus, AgentLifecycleStatus
from agent_platform.models.agent import AgentModel


def agent_to_domain(model: AgentModel) -> Agent:
    return Agent(
        id=model.id, workspace_id=model.workspace_id, agent_type_id=model.agent_type_id, name=model.name,
        role=model.role, instructions=model.instructions, goals=list(model.goals or []),
        capabilities=list(model.capabilities or []), skills=list(model.skills or []),
        resource_limits=dict(model.resource_limits or {}), is_autonomous=model.is_autonomous,
        status=AgentLifecycleStatus(model.status), health_status=AgentHealthStatus(model.health_status), version=model.version,
    )


def apply_agent_domain_to_model(entity: Agent, model: AgentModel) -> None:
    model.status = entity.status.value
    model.health_status = entity.health_status.value
    model.goals = entity.goals
    model.capabilities = entity.capabilities
    model.skills = entity.skills
    model.resource_limits = entity.resource_limits
    model.is_autonomous = entity.is_autonomous
