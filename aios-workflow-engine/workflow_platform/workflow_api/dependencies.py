"""FastAPI dependency wiring: DB session -> RepositoryRegistry -> every
service, plus AI Core and a minimal caller-identity dependency.

Auth is intentionally minimal here: this platform expects to sit behind
an already-authenticated gateway (e.g. the AIOS backend from Phase 3)
that forwards the caller's identity via the `X-User-Id` header — the
same seam the Prompt/Agent Platforms use. Every router depends on
`get_current_actor_id`, never on the header directly, so swapping in
real token validation later is a one-file change.

The Execution Engine's bridges and node-handler registry are stateful
(the reference Memory/Knowledge bridges hold in-memory stores) and
expensive-ish to build, so they're cached process-wide via `lru_cache`
rather than rebuilt per request — the same pattern the Agent Platform
uses for its shared memory backend. The engine itself, and the
`RepositoryRegistry`/session it wraps, are still built fresh per
request, since a `AsyncSession` must never be shared across concurrent
requests."""
from __future__ import annotations

from collections.abc import AsyncGenerator
from functools import lru_cache

from ai_core.bootstrap import AICoreContext
from fastapi import Depends, Header, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from workflow_platform.ai_bridges.interfaces import BridgeSet
from workflow_platform.ai_bridges.reference_bridges import build_reference_bridge_set
from workflow_platform.approval.approval_service import ApprovalService
from workflow_platform.config.settings import Settings, get_settings
from workflow_platform.database.session import get_db_session
from workflow_platform.dependencies.ai_core_provider import get_default_ai_core_context
from workflow_platform.events.event_bus import EventBus
from workflow_platform.events.subscription_service import SubscriptionService
from workflow_platform.monitoring.observability_service import ObservabilityService
from workflow_platform.recovery.recovery_service import RecoveryService
from workflow_platform.repositories.registry import RepositoryRegistry
from workflow_platform.scheduler.dispatcher import SchedulerDispatcher
from workflow_platform.scheduler.scheduler_service import ScheduleService
from workflow_platform.security.audit_service import AuditService
from workflow_platform.security.policy_service import ApprovalPolicyService, ExecutionPolicyService
from workflow_platform.security.rbac_service import RBACService
from workflow_platform.state.execution_state_service import ExecutionStateService
from workflow_platform.state.variable_service import VariableService
from workflow_platform.workflow_core.version_service import WorkflowVersionService
from workflow_platform.workflow_core.workflow_service import WorkflowService
from workflow_platform.workflow_engine.engine import ExecutionEngine
from workflow_platform.workflow_engine.registry import HandlerRegistry, build_default_handler_registry


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    async for session in get_db_session():
        yield session


async def get_repos(session: AsyncSession = Depends(get_session)) -> RepositoryRegistry:
    return RepositoryRegistry(session)


def get_ai_core() -> AICoreContext:
    return get_default_ai_core_context()


def get_settings_dep() -> Settings:
    return get_settings()


async def get_current_actor_id(x_user_id: str | None = Header(default=None)) -> str:
    if not x_user_id:
        raise HTTPException(status_code=401, detail="Missing X-User-Id header")
    return x_user_id


@lru_cache
def _shared_bridge_set() -> BridgeSet:
    return build_reference_bridge_set()


@lru_cache
def _shared_handler_registry() -> HandlerRegistry:
    return build_default_handler_registry(bridges=_shared_bridge_set())


# -- workflow core -----------------------------------------------------------------

def get_workflow_service(repos: RepositoryRegistry = Depends(get_repos)) -> WorkflowService:
    return WorkflowService(repos)


def get_version_service(repos: RepositoryRegistry = Depends(get_repos)) -> WorkflowVersionService:
    return WorkflowVersionService(repos)


# -- execution engine (+ everything that piggybacks on its event bus) --------------

def get_execution_engine(
    repos: RepositoryRegistry = Depends(get_repos), ai_core: AICoreContext = Depends(get_ai_core),
    settings: Settings = Depends(get_settings_dep),
) -> ExecutionEngine:
    engine = ExecutionEngine(
        repos, _shared_handler_registry(), ai_core=ai_core, bridges=_shared_bridge_set(),
        max_recursion_depth=settings.max_workflow_recursion_depth, approval_policy=ApprovalPolicyService(),
    )
    engine.event_bus = EventBus(repos, lock=engine._session_lock)
    engine._extra["event_publisher"] = engine.event_bus.publish
    return engine


def get_event_bus(engine: ExecutionEngine = Depends(get_execution_engine)) -> EventBus:
    return engine.event_bus


def get_subscription_service(repos: RepositoryRegistry = Depends(get_repos)) -> SubscriptionService:
    return SubscriptionService(repos)


def get_scheduler_dispatcher(
    repos: RepositoryRegistry = Depends(get_repos), engine: ExecutionEngine = Depends(get_execution_engine),
) -> SchedulerDispatcher:
    return SchedulerDispatcher(repos, engine)


def get_schedule_service(repos: RepositoryRegistry = Depends(get_repos)) -> ScheduleService:
    return ScheduleService(repos)


def get_approval_service(
    repos: RepositoryRegistry = Depends(get_repos), engine: ExecutionEngine = Depends(get_execution_engine),
) -> ApprovalService:
    return ApprovalService(repos, engine=engine, event_bus=engine.event_bus)


# -- state / recovery / observability ------------------------------------------------

def get_variable_service(repos: RepositoryRegistry = Depends(get_repos)) -> VariableService:
    return VariableService(repos)


def get_execution_state_service(repos: RepositoryRegistry = Depends(get_repos)) -> ExecutionStateService:
    return ExecutionStateService(repos)


def get_recovery_service(repos: RepositoryRegistry = Depends(get_repos)) -> RecoveryService:
    return RecoveryService(repos)


def get_observability_service(repos: RepositoryRegistry = Depends(get_repos)) -> ObservabilityService:
    return ObservabilityService(repos)


# -- security / governance -----------------------------------------------------------

def get_rbac_service(repos: RepositoryRegistry = Depends(get_repos)) -> RBACService:
    return RBACService(repos)


def get_audit_service(repos: RepositoryRegistry = Depends(get_repos)) -> AuditService:
    return AuditService(repos)


def get_execution_policy_service(rbac: RBACService = Depends(get_rbac_service)) -> ExecutionPolicyService:
    return ExecutionPolicyService(rbac)


def get_approval_policy_service() -> ApprovalPolicyService:
    return ApprovalPolicyService()
