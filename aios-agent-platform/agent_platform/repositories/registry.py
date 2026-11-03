"""Wires every repository to one shared AsyncSession — used by UnitOfWork
so a service can touch multiple aggregates within a single transaction."""
from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from agent_platform.repositories.agent_repository import AgentRepository
from agent_platform.repositories.agent_type_repository import AgentTypeRepository
from agent_platform.repositories.delegation_repository import DelegationRepository
from agent_platform.repositories.execution_repository import AgentExecutionRepository, ExecutionCheckpointRepository
from agent_platform.repositories.governance_repository import (
    ApprovalGateRepository,
    AuditLogEntryRepository,
    PermissionGrantRepository,
)
from agent_platform.repositories.message_repository import MessageRepository, SharedWorkspaceRepository
from agent_platform.repositories.reasoning_repository import ReasoningTraceRepository, ReflectionRepository
from agent_platform.repositories.task_repository import TaskDependencyRepository, TaskRepository
from agent_platform.repositories.tool_permission_repository import AgentToolPermissionRepository
from agent_platform.repositories.workspace_repository import WorkspaceRepository


class RepositoryRegistry:
    def __init__(self, session: AsyncSession):
        self.session = session
        self.workspaces = WorkspaceRepository(session)
        self.agent_types = AgentTypeRepository(session)
        self.agents = AgentRepository(session)
        self.tool_permissions = AgentToolPermissionRepository(session)
        self.tasks = TaskRepository(session)
        self.task_dependencies = TaskDependencyRepository(session)
        self.delegations = DelegationRepository(session)
        self.executions = AgentExecutionRepository(session)
        self.checkpoints = ExecutionCheckpointRepository(session)
        self.messages = MessageRepository(session)
        self.shared_workspace = SharedWorkspaceRepository(session)
        self.reasoning_traces = ReasoningTraceRepository(session)
        self.reflections = ReflectionRepository(session)
        self.approval_gates = ApprovalGateRepository(session)
        self.audit_log = AuditLogEntryRepository(session)
        self.permission_grants = PermissionGrantRepository(session)
