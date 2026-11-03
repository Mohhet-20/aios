"""Unit-of-work: one shared `AsyncSession` backing every repository,
lazily memoized. Identical pattern to every prior AIOS platform."""
from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from developer_platform.repositories.analytics_repository import UsageEventRepository
from developer_platform.repositories.api_platform_repository import (
    ApiKeyRepository,
    ApiUsageRecordRepository,
    ApiVersionRepository,
)
from developer_platform.repositories.cli_repository import CliCommandLogRepository, CliSessionRepository
from developer_platform.repositories.codegen_repository import CodeGenArtifactRepository, CodeGenJobRepository
from developer_platform.repositories.extensions_repository import (
    ExtensionPointRepository,
    ExtensionRegistrationRepository,
)
from developer_platform.repositories.mcp_repository import (
    McpPromptRepository,
    McpResourceRepository,
    McpServerRepository,
    McpSessionRepository,
    McpToolRepository,
)
from developer_platform.repositories.plugins_repository import (
    PluginDependencyRepository,
    PluginMarketplaceListingRepository,
    PluginRepository,
    PluginVersionRepository,
)
from developer_platform.repositories.portal_repository import (
    PortalContentRepository,
    SandboxEnvironmentRepository,
)
from developer_platform.repositories.registry_repository import (
    RegistryPackageRepository,
    RegistryPackageVersionRepository,
)
from developer_platform.repositories.sdk_repository import SdkCompatibilityEntryRepository
from developer_platform.repositories.security_repository import (
    DeveloperRoleBindingRepository,
    SecretReferenceRepository,
)
from developer_platform.repositories.webhooks_repository import (
    WebhookDeliveryRepository,
    WebhookSubscriptionRepository,
)


class RepositoryRegistry:
    def __init__(self, session: AsyncSession):
        self.session = session
        self._cache: dict[str, object] = {}

    def _get(self, key: str, cls: type):
        if key not in self._cache:
            self._cache[key] = cls(self.session)
        return self._cache[key]

    # -- api platform ---------------------------------------------------------------------
    @property
    def api_keys(self) -> ApiKeyRepository:
        return self._get("api_keys", ApiKeyRepository)

    @property
    def api_usage_records(self) -> ApiUsageRecordRepository:
        return self._get("api_usage_records", ApiUsageRecordRepository)

    @property
    def api_versions(self) -> ApiVersionRepository:
        return self._get("api_versions", ApiVersionRepository)

    # -- sdk platform -----------------------------------------------------------------------
    @property
    def sdk_compatibility_entries(self) -> SdkCompatibilityEntryRepository:
        return self._get("sdk_compatibility_entries", SdkCompatibilityEntryRepository)

    # -- cli platform -----------------------------------------------------------------------
    @property
    def cli_sessions(self) -> CliSessionRepository:
        return self._get("cli_sessions", CliSessionRepository)

    @property
    def cli_command_logs(self) -> CliCommandLogRepository:
        return self._get("cli_command_logs", CliCommandLogRepository)

    # -- plugin sdk -------------------------------------------------------------------------
    @property
    def plugins(self) -> PluginRepository:
        return self._get("plugins", PluginRepository)

    @property
    def plugin_versions(self) -> PluginVersionRepository:
        return self._get("plugin_versions", PluginVersionRepository)

    @property
    def plugin_dependencies(self) -> PluginDependencyRepository:
        return self._get("plugin_dependencies", PluginDependencyRepository)

    @property
    def plugin_marketplace_listings(self) -> PluginMarketplaceListingRepository:
        return self._get("plugin_marketplace_listings", PluginMarketplaceListingRepository)

    # -- extension framework ------------------------------------------------------------------
    @property
    def extension_points(self) -> ExtensionPointRepository:
        return self._get("extension_points", ExtensionPointRepository)

    @property
    def extension_registrations(self) -> ExtensionRegistrationRepository:
        return self._get("extension_registrations", ExtensionRegistrationRepository)

    # -- webhook platform ---------------------------------------------------------------------
    @property
    def webhook_subscriptions(self) -> WebhookSubscriptionRepository:
        return self._get("webhook_subscriptions", WebhookSubscriptionRepository)

    @property
    def webhook_deliveries(self) -> WebhookDeliveryRepository:
        return self._get("webhook_deliveries", WebhookDeliveryRepository)

    # -- mcp integration ----------------------------------------------------------------------
    @property
    def mcp_servers(self) -> McpServerRepository:
        return self._get("mcp_servers", McpServerRepository)

    @property
    def mcp_sessions(self) -> McpSessionRepository:
        return self._get("mcp_sessions", McpSessionRepository)

    @property
    def mcp_resources(self) -> McpResourceRepository:
        return self._get("mcp_resources", McpResourceRepository)

    @property
    def mcp_tools(self) -> McpToolRepository:
        return self._get("mcp_tools", McpToolRepository)

    @property
    def mcp_prompts(self) -> McpPromptRepository:
        return self._get("mcp_prompts", McpPromptRepository)

    # -- code generation ----------------------------------------------------------------------
    @property
    def codegen_jobs(self) -> CodeGenJobRepository:
        return self._get("codegen_jobs", CodeGenJobRepository)

    @property
    def codegen_artifacts(self) -> CodeGenArtifactRepository:
        return self._get("codegen_artifacts", CodeGenArtifactRepository)

    # -- developer portal & sandbox -------------------------------------------------------------
    @property
    def portal_content(self) -> PortalContentRepository:
        return self._get("portal_content", PortalContentRepository)

    @property
    def sandbox_environments(self) -> SandboxEnvironmentRepository:
        return self._get("sandbox_environments", SandboxEnvironmentRepository)

    # -- package registry ---------------------------------------------------------------------
    @property
    def registry_packages(self) -> RegistryPackageRepository:
        return self._get("registry_packages", RegistryPackageRepository)

    @property
    def registry_package_versions(self) -> RegistryPackageVersionRepository:
        return self._get("registry_package_versions", RegistryPackageVersionRepository)

    # -- developer analytics -------------------------------------------------------------------
    @property
    def usage_events(self) -> UsageEventRepository:
        return self._get("usage_events", UsageEventRepository)

    # -- security -------------------------------------------------------------------------------
    @property
    def developer_role_bindings(self) -> DeveloperRoleBindingRepository:
        return self._get("developer_role_bindings", DeveloperRoleBindingRepository)

    @property
    def secret_references(self) -> SecretReferenceRepository:
        return self._get("secret_references", SecretReferenceRepository)
