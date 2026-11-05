"""FastAPI dependency wiring: DB session -> RepositoryRegistry -> every
service, plus AI Core and a minimal caller-identity dependency.

Auth is intentionally minimal here: this platform expects to sit behind
an already-authenticated gateway that forwards the caller's identity via
the `X-User-Id` header — the same seam every sibling AIOS platform uses.
Every router depends on `get_current_actor_id`, never on the header
directly, so swapping in real token validation later is a one-file
change.

The connector registry and platform integration bridges are stateful-ish
and a little expensive to construct, so they're cached process-wide via
`lru_cache` rather than rebuilt per request — the same pattern the
Workflow Engine uses for its handler registry. The engine itself, and
the `RepositoryRegistry`/session it wraps, are still built fresh per
request, since an `AsyncSession` must never be shared across concurrent
requests."""
from __future__ import annotations

from collections.abc import AsyncGenerator
from functools import lru_cache

from ai_core.bootstrap import AICoreContext
from fastapi import Depends, Header, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from tool_platform.ai_planning.planning_service import ToolPlanningService
from tool_platform.config.settings import Settings, get_settings
from tool_platform.credentials.vault_service import VaultService
from tool_platform.database.session import get_db_session
from tool_platform.dependencies.ai_core_provider import get_default_ai_core_context
from tool_platform.discovery.discovery_service import ToolDiscoveryService
from tool_platform.governance.approval_service import ApprovalService
from tool_platform.governance.audit_service import AuditService
from tool_platform.governance.policy_engine import PolicyEngine
from tool_platform.governance.rbac_service import RBACService
from tool_platform.marketplace.marketplace_service import MarketplaceService
from tool_platform.monitoring.observability_service import ObservabilityService
from tool_platform.plugin_system.installation_service import PluginInstallationService
from tool_platform.plugin_system.registry_service import PluginRegistryService
from tool_platform.platform_bridges.interfaces import PlatformBridgeSet
from tool_platform.platform_bridges.reference_bridges import build_reference_bridge_set
from tool_platform.repositories.registry import RepositoryRegistry
from tool_platform.scheduler.dispatcher import ScheduleDispatcher
from tool_platform.scheduler.schedule_service import ScheduleService
from tool_platform.sandbox.network_policy import NetworkPolicy
from tool_platform.tool_core.tool_service import ToolService
from tool_platform.tool_core.version_service import ToolVersionService
from tool_platform.tool_execution.engine import ToolExecutionEngine
from tool_platform.tool_execution.registry import ConnectorRegistry, build_default_connector_registry


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


@lru_cache
def _shared_connector_registry() -> ConnectorRegistry:
    return build_default_connector_registry()


@lru_cache
def _shared_bridge_set() -> PlatformBridgeSet:
    return build_reference_bridge_set()


@lru_cache
def _shared_network_policy() -> NetworkPolicy:
    from tool_platform.domain.enums import SandboxNetworkPolicy

    settings = get_settings()
    policy_type = SandboxNetworkPolicy.DENY_ALL if settings.sandbox_network_default_deny else SandboxNetworkPolicy.ALLOW_ALL
    return NetworkPolicy(policy_type=policy_type)


# -- tool core -----------------------------------------------------------------

def get_tool_service(repos: RepositoryRegistry = Depends(get_repos)) -> ToolService:
    return ToolService(repos)


def get_version_service(repos: RepositoryRegistry = Depends(get_repos)) -> ToolVersionService:
    return ToolVersionService(repos)


# -- discovery / planning --------------------------------------------------------

def get_discovery_service(repos: RepositoryRegistry = Depends(get_repos)) -> ToolDiscoveryService:
    return ToolDiscoveryService(repos)


def get_planning_service(
    repos: RepositoryRegistry = Depends(get_repos), discovery: ToolDiscoveryService = Depends(get_discovery_service),
) -> ToolPlanningService:
    return ToolPlanningService(repos, discovery)


# -- credentials -----------------------------------------------------------------

def get_vault_service(repos: RepositoryRegistry = Depends(get_repos)) -> VaultService:
    return VaultService(repos)


# -- plugins / marketplace --------------------------------------------------------

def get_plugin_registry_service(
    repos: RepositoryRegistry = Depends(get_repos), settings: Settings = Depends(get_settings_dep),
) -> PluginRegistryService:
    return PluginRegistryService(repos, secret_key=settings.secret_key)


def get_plugin_installation_service(
    repos: RepositoryRegistry = Depends(get_repos), settings: Settings = Depends(get_settings_dep),
) -> PluginInstallationService:
    return PluginInstallationService(repos, secret_key=settings.secret_key, require_signature=settings.require_plugin_signature)


def get_marketplace_service(repos: RepositoryRegistry = Depends(get_repos)) -> MarketplaceService:
    return MarketplaceService(repos)


# -- governance --------------------------------------------------------------------

def get_rbac_service(repos: RepositoryRegistry = Depends(get_repos)) -> RBACService:
    return RBACService(repos)


def get_policy_engine(
    repos: RepositoryRegistry = Depends(get_repos), settings: Settings = Depends(get_settings_dep),
) -> PolicyEngine:
    return PolicyEngine(repos, settings)


def get_approval_service(repos: RepositoryRegistry = Depends(get_repos)) -> ApprovalService:
    return ApprovalService(repos)


def get_audit_service(repos: RepositoryRegistry = Depends(get_repos)) -> AuditService:
    return AuditService(repos)


# -- execution engine (+ everything that piggybacks on governance) -----------------

def get_execution_engine(
    repos: RepositoryRegistry = Depends(get_repos), ai_core: AICoreContext = Depends(get_ai_core),
    vault: VaultService = Depends(get_vault_service),
    policy_engine: PolicyEngine = Depends(get_policy_engine),
    approval_service: ApprovalService = Depends(get_approval_service),
    audit_service: AuditService = Depends(get_audit_service),
) -> ToolExecutionEngine:
    return ToolExecutionEngine(
        repos, _shared_connector_registry(), vault=vault, ai_core=ai_core, network_policy=_shared_network_policy(),
        policy_engine=policy_engine, approval_service=approval_service, audit_service=audit_service,
    )


# -- scheduling ----------------------------------------------------------------------

def get_schedule_service(repos: RepositoryRegistry = Depends(get_repos)) -> ScheduleService:
    return ScheduleService(repos)


def get_schedule_dispatcher(
    repos: RepositoryRegistry = Depends(get_repos), engine: ToolExecutionEngine = Depends(get_execution_engine),
) -> ScheduleDispatcher:
    return ScheduleDispatcher(repos, engine)


# -- observability -------------------------------------------------------------------

def get_observability_service(repos: RepositoryRegistry = Depends(get_repos)) -> ObservabilityService:
    return ObservabilityService(repos)
