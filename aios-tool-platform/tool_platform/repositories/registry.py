"""RepositoryRegistry: wires every repository to one shared AsyncSession,
so a single unit-of-work-scoped session backs every repository an
application-service call touches. Same pattern as every prior AIOS
platform's `RepositoryRegistry`."""
from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from tool_platform.repositories.checkpoint_repository import ExecutionCheckpointRepository
from tool_platform.repositories.credential_repository import CredentialRepository, ToolCredentialBindingRepository
from tool_platform.repositories.discovery_repository import ToolFavoriteRepository
from tool_platform.repositories.execution_repository import ToolExecutionRepository
from tool_platform.repositories.governance_repository import (
    ApprovalGateRepository,
    AuditLogEntryRepository,
    PermissionGrantRepository,
)
from tool_platform.repositories.observability_repository import ExecutionLogRepository
from tool_platform.repositories.plugin_repository import (
    PluginDependencyRepository,
    PluginInstallationRepository,
    PluginRepository,
)
from tool_platform.repositories.schedule_repository import ToolScheduleRepository
from tool_platform.repositories.tool_repository import ToolRepository, ToolVersionRepository
from tool_platform.repositories.workspace_repository import WorkspaceRepository


class RepositoryRegistry:
    """One instance per unit-of-work session; exposes every repository as
    a lazily-constructed, memoized property so services only pay for the
    repositories they actually touch."""

    def __init__(self, session: AsyncSession):
        self.session = session
        self._cache: dict[str, object] = {}

    def _get(self, key: str, cls: type):
        if key not in self._cache:
            self._cache[key] = cls(self.session)
        return self._cache[key]

    @property
    def workspaces(self) -> WorkspaceRepository:
        return self._get("workspaces", WorkspaceRepository)

    @property
    def tools(self) -> ToolRepository:
        return self._get("tools", ToolRepository)

    @property
    def tool_versions(self) -> ToolVersionRepository:
        return self._get("tool_versions", ToolVersionRepository)

    @property
    def plugins(self) -> PluginRepository:
        return self._get("plugins", PluginRepository)

    @property
    def plugin_dependencies(self) -> PluginDependencyRepository:
        return self._get("plugin_dependencies", PluginDependencyRepository)

    @property
    def plugin_installations(self) -> PluginInstallationRepository:
        return self._get("plugin_installations", PluginInstallationRepository)

    @property
    def credentials(self) -> CredentialRepository:
        return self._get("credentials", CredentialRepository)

    @property
    def tool_credential_bindings(self) -> ToolCredentialBindingRepository:
        return self._get("tool_credential_bindings", ToolCredentialBindingRepository)

    @property
    def executions(self) -> ToolExecutionRepository:
        return self._get("executions", ToolExecutionRepository)

    @property
    def checkpoints(self) -> ExecutionCheckpointRepository:
        return self._get("checkpoints", ExecutionCheckpointRepository)

    @property
    def schedules(self) -> ToolScheduleRepository:
        return self._get("schedules", ToolScheduleRepository)

    @property
    def permission_grants(self) -> PermissionGrantRepository:
        return self._get("permission_grants", PermissionGrantRepository)

    @property
    def approval_gates(self) -> ApprovalGateRepository:
        return self._get("approval_gates", ApprovalGateRepository)

    @property
    def audit_log(self) -> AuditLogEntryRepository:
        return self._get("audit_log", AuditLogEntryRepository)

    @property
    def execution_logs(self) -> ExecutionLogRepository:
        return self._get("execution_logs", ExecutionLogRepository)

    @property
    def tool_favorites(self) -> ToolFavoriteRepository:
        return self._get("tool_favorites", ToolFavoriteRepository)
