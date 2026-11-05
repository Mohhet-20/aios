"""FastAPI dependency wiring: DB session -> RepositoryRegistry -> every
service, plus AI Core and a minimal caller-identity dependency.

Auth is intentionally minimal here: this platform expects to sit behind
an already-authenticated gateway (e.g. the AIOS core backend,
which owns full JWT/session auth) that forwards the caller's identity via
the `X-User-Id` header — the same seam the Prompt Platform uses. Every
router depends on `get_current_actor_id`, never on the header directly,
so swapping in real token validation later is a one-file change.
"""
from __future__ import annotations

from collections.abc import AsyncGenerator

from ai_core.bootstrap import AICoreContext
from fastapi import Depends, Header, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from functools import lru_cache

from agent_platform.agent_memory.in_memory_backend import InMemoryMemoryBackend
from agent_platform.agent_memory.memory_service import MemoryService
from agent_platform.agent_registry.agent_service import AgentService
from agent_platform.agent_registry.type_service import AgentTypeService
from agent_platform.analytics.analytics_service import AnalyticsService
from agent_platform.communication.communication_service import CommunicationService
from agent_platform.config.settings import Settings, get_settings
from agent_platform.coordination.orchestrator import TaskOrchestrator
from agent_platform.database.session import get_db_session
from agent_platform.dependencies.ai_core_provider import get_default_ai_core_context
from agent_platform.evaluation.evaluation_service import EvaluationService
from agent_platform.monitoring.observability_service import ObservabilityService
from agent_platform.permissions.rbac_service import RBACService
from agent_platform.planner.planning_service import PlanningService
from agent_platform.policies.approval_service import ApprovalService
from agent_platform.policies.audit_service import AuditService
from agent_platform.policies.policy_engine import PolicyEngine
from agent_platform.reasoning.reasoning_service import ReasoningService
from agent_platform.reflection.reflection_service import ReflectionService
from agent_platform.repositories.registry import RepositoryRegistry
from agent_platform.tool_bridge.tool_bridge_service import ToolBridgeService


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    async for session in get_db_session():
        yield session


async def get_repos(session: AsyncSession = Depends(get_session, scope="function")) -> RepositoryRegistry:
    return RepositoryRegistry(session)


def get_ai_core() -> AICoreContext:
    return get_default_ai_core_context()


def get_settings_dep() -> Settings:
    return get_settings()


async def get_current_actor_id(x_user_id: str | None = Header(default=None)) -> str:
    if not x_user_id:
        raise HTTPException(status_code=401, detail="Missing X-User-Id header")
    return x_user_id


# -- per-service factories ----------------------------------------------------------

def get_agent_type_service(repos: RepositoryRegistry = Depends(get_repos)) -> AgentTypeService:
    return AgentTypeService(repos)


def get_agent_service(repos: RepositoryRegistry = Depends(get_repos)) -> AgentService:
    return AgentService(repos)


def get_planning_service(
    repos: RepositoryRegistry = Depends(get_repos), ai_core: AICoreContext = Depends(get_ai_core),
    settings: Settings = Depends(get_settings_dep),
) -> PlanningService:
    return PlanningService(repos, ai_core, max_recursion_depth=settings.max_agent_recursion_depth)


def get_communication_service(repos: RepositoryRegistry = Depends(get_repos)) -> CommunicationService:
    return CommunicationService(repos)


def get_policy_engine(
    repos: RepositoryRegistry = Depends(get_repos), settings: Settings = Depends(get_settings_dep),
) -> PolicyEngine:
    return PolicyEngine(repos, settings)


def get_approval_service(repos: RepositoryRegistry = Depends(get_repos)) -> ApprovalService:
    return ApprovalService(repos)


def get_audit_service(repos: RepositoryRegistry = Depends(get_repos)) -> AuditService:
    return AuditService(repos)


def get_rbac_service(repos: RepositoryRegistry = Depends(get_repos)) -> RBACService:
    return RBACService(repos)


def get_orchestrator(
    repos: RepositoryRegistry = Depends(get_repos), ai_core: AICoreContext = Depends(get_ai_core),
    communication: CommunicationService = Depends(get_communication_service),
    policy_engine: PolicyEngine = Depends(get_policy_engine),
    approval_service: ApprovalService = Depends(get_approval_service),
) -> TaskOrchestrator:
    return TaskOrchestrator(repos, ai_core, communication=communication, policy_engine=policy_engine, approval_service=approval_service)


def get_reasoning_service(
    repos: RepositoryRegistry = Depends(get_repos), ai_core: AICoreContext = Depends(get_ai_core),
) -> ReasoningService:
    return ReasoningService(repos, ai_core)


def get_reflection_service(
    repos: RepositoryRegistry = Depends(get_repos), ai_core: AICoreContext = Depends(get_ai_core),
) -> ReflectionService:
    return ReflectionService(repos, ai_core)


def get_tool_bridge_service(
    repos: RepositoryRegistry = Depends(get_repos), ai_core: AICoreContext = Depends(get_ai_core),
) -> ToolBridgeService:
    return ToolBridgeService(repos, ai_core)


@lru_cache
def _shared_memory_backend() -> InMemoryMemoryBackend:
    """One process-wide backend instance, not a fresh one per request —
    MemoryService itself defaults to a new backend per instantiation
    (correct for tests, which want isolation), but a real API server
    needs writes from one request to be visible to the next."""
    return InMemoryMemoryBackend()


def get_memory_service(repos: RepositoryRegistry = Depends(get_repos)) -> MemoryService:
    return MemoryService(repos, backend=_shared_memory_backend())


def get_observability_service(repos: RepositoryRegistry = Depends(get_repos)) -> ObservabilityService:
    return ObservabilityService(repos)


def get_analytics_service(repos: RepositoryRegistry = Depends(get_repos)) -> AnalyticsService:
    return AnalyticsService(repos)


def get_evaluation_service(repos: RepositoryRegistry = Depends(get_repos)) -> EvaluationService:
    return EvaluationService(repos)
