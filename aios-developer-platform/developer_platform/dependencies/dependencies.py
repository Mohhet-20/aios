"""FastAPI dependency wiring: DB session -> RepositoryRegistry ->
every service. Auth is intentionally minimal here, matching every
sibling AIOS platform: this platform expects to sit behind an
already-authenticated gateway (in practice, the Identity Platform)
that forwards the caller's tenant via `X-Tenant-Id` and, where
relevant, the acting principal via `X-User-Id`. Every service is
built fresh per request off a per-request `RepositoryRegistry`/
`AsyncSession`, since a session must never be shared across
concurrent requests."""
from __future__ import annotations

from collections.abc import AsyncGenerator

from fastapi import Depends, Header, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from developer_platform.api_platform.api_key_service import ApiKeyService
from developer_platform.api_platform.openapi_service import OpenApiSpecService
from developer_platform.api_platform.rate_limit_service import RateLimiterService
from developer_platform.api_platform.version_service import ApiVersionService
from developer_platform.cli_platform.command_log_service import CliCommandLogService
from developer_platform.cli_platform.session_service import CliSessionService
from developer_platform.codegen.engine import CodeGenEngine
from developer_platform.config.settings import Settings, get_settings
from developer_platform.database.session import session_scope
from developer_platform.developer_analytics.dashboard_service import DeveloperActivityDashboardService
from developer_platform.developer_analytics.usage_service import UsageAnalyticsService
from developer_platform.developer_portal.content_service import PortalContentService
from developer_platform.developer_portal.sandbox_service import SandboxService
from developer_platform.dev_security.oauth_readiness_service import OAuthReadinessService
from developer_platform.dev_security.plugin_isolation_service import PluginIsolationService
from developer_platform.dev_security.rbac_service import DeveloperRbacService
from developer_platform.dev_security.secret_reference_service import SecretReferenceService
from developer_platform.extension_framework.point_service import ExtensionPointService
from developer_platform.extension_framework.registration_service import ExtensionRegistrationService
from developer_platform.mcp_integration.discovery_service import McpDiscoveryService
from developer_platform.mcp_integration.server_service import McpServerService
from developer_platform.mcp_integration.session_service import McpSessionService
from developer_platform.plugin_sdk.dependency_service import PluginDependencyService
from developer_platform.plugin_sdk.lifecycle_service import PluginLifecycleService
from developer_platform.plugin_sdk.marketplace_service import PluginMarketplaceService
from developer_platform.plugin_sdk.packaging_service import PluginPackagingService
from developer_platform.registry_platform.dependency_service import PackageDependencyService
from developer_platform.registry_platform.package_service import PackageRegistryService
from developer_platform.repositories.registry import RepositoryRegistry
from developer_platform.sdk_platform.compatibility_service import SdkCompatibilityService
from developer_platform.sdk_platform.package_service import SdkPackageService
from developer_platform.webhook_platform.delivery_service import WebhookDeliveryService
from developer_platform.webhook_platform.subscription_service import WebhookSubscriptionService


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    """Delegates to `session_scope`, which commits on a clean exit and
    rolls back on any exception — a request handled through the REST
    API needs its writes to actually persist once the response is
    returned."""
    async for session in session_scope():
        yield session


async def get_repos(session: AsyncSession = Depends(get_session)) -> RepositoryRegistry:
    return RepositoryRegistry(session)


def get_settings_dep() -> Settings:
    return get_settings()


async def get_current_tenant_id(x_tenant_id: str | None = Header(default=None)) -> str:
    if not x_tenant_id:
        raise HTTPException(status_code=400, detail="Missing X-Tenant-Id header")
    return x_tenant_id


async def get_current_actor_id(x_user_id: str | None = Header(default=None)) -> str | None:
    """Unlike the tenant header, the actor header is optional — some
    of what this platform tracks (scheduled retention sweeps, CI
    triggers, automated scaling decisions) legitimately comes from a
    process with no human actor behind it."""
    return x_user_id


# -- api platform ---------------------------------------------------------------------------
async def get_api_key_service(repos: RepositoryRegistry = Depends(get_repos)) -> ApiKeyService:
    return ApiKeyService(repos)


async def get_rate_limiter_service(repos: RepositoryRegistry = Depends(get_repos)) -> RateLimiterService:
    return RateLimiterService(repos)


async def get_api_version_service(repos: RepositoryRegistry = Depends(get_repos)) -> ApiVersionService:
    return ApiVersionService(repos)


async def get_openapi_spec_service() -> OpenApiSpecService:
    return OpenApiSpecService()


# -- sdk platform -----------------------------------------------------------------------------
async def get_sdk_compatibility_service(repos: RepositoryRegistry = Depends(get_repos)) -> SdkCompatibilityService:
    return SdkCompatibilityService(repos)


async def get_sdk_package_service(repos: RepositoryRegistry = Depends(get_repos)) -> SdkPackageService:
    return SdkPackageService(repos)


# -- cli platform -----------------------------------------------------------------------------
async def get_cli_session_service(repos: RepositoryRegistry = Depends(get_repos)) -> CliSessionService:
    return CliSessionService(repos)


async def get_cli_command_log_service(repos: RepositoryRegistry = Depends(get_repos)) -> CliCommandLogService:
    return CliCommandLogService(repos)


# -- plugin sdk -------------------------------------------------------------------------------
async def get_plugin_lifecycle_service(repos: RepositoryRegistry = Depends(get_repos)) -> PluginLifecycleService:
    return PluginLifecycleService(repos)


async def get_plugin_packaging_service(repos: RepositoryRegistry = Depends(get_repos)) -> PluginPackagingService:
    return PluginPackagingService(repos)


async def get_plugin_dependency_service(repos: RepositoryRegistry = Depends(get_repos)) -> PluginDependencyService:
    return PluginDependencyService(repos)


async def get_plugin_marketplace_service(repos: RepositoryRegistry = Depends(get_repos)) -> PluginMarketplaceService:
    return PluginMarketplaceService(repos)


# -- extension framework ------------------------------------------------------------------------
async def get_extension_point_service(repos: RepositoryRegistry = Depends(get_repos)) -> ExtensionPointService:
    return ExtensionPointService(repos)


async def get_extension_registration_service(repos: RepositoryRegistry = Depends(get_repos)) -> ExtensionRegistrationService:
    return ExtensionRegistrationService(repos)


# -- webhook platform ---------------------------------------------------------------------------
async def get_webhook_subscription_service(repos: RepositoryRegistry = Depends(get_repos)) -> WebhookSubscriptionService:
    return WebhookSubscriptionService(repos)


async def get_webhook_delivery_service(repos: RepositoryRegistry = Depends(get_repos)) -> WebhookDeliveryService:
    return WebhookDeliveryService(repos)


# -- mcp integration ----------------------------------------------------------------------------
async def get_mcp_server_service(repos: RepositoryRegistry = Depends(get_repos)) -> McpServerService:
    return McpServerService(repos)


async def get_mcp_session_service(repos: RepositoryRegistry = Depends(get_repos)) -> McpSessionService:
    return McpSessionService(repos)


async def get_mcp_discovery_service(repos: RepositoryRegistry = Depends(get_repos)) -> McpDiscoveryService:
    return McpDiscoveryService(repos)


# -- code generation ----------------------------------------------------------------------------
async def get_codegen_engine(repos: RepositoryRegistry = Depends(get_repos)) -> CodeGenEngine:
    return CodeGenEngine(repos)


# -- developer portal & sandbox -------------------------------------------------------------------
async def get_portal_content_service(repos: RepositoryRegistry = Depends(get_repos)) -> PortalContentService:
    return PortalContentService(repos)


async def get_sandbox_service(repos: RepositoryRegistry = Depends(get_repos)) -> SandboxService:
    return SandboxService(repos)


# -- package registry ---------------------------------------------------------------------------
async def get_package_registry_service(repos: RepositoryRegistry = Depends(get_repos)) -> PackageRegistryService:
    return PackageRegistryService(repos)


async def get_package_dependency_service(repos: RepositoryRegistry = Depends(get_repos)) -> PackageDependencyService:
    return PackageDependencyService(repos)


# -- developer analytics -------------------------------------------------------------------------
async def get_usage_analytics_service(repos: RepositoryRegistry = Depends(get_repos)) -> UsageAnalyticsService:
    return UsageAnalyticsService(repos)


async def get_dashboard_service(repos: RepositoryRegistry = Depends(get_repos)) -> DeveloperActivityDashboardService:
    return DeveloperActivityDashboardService(repos)


# -- security -------------------------------------------------------------------------------------
async def get_rbac_service(repos: RepositoryRegistry = Depends(get_repos)) -> DeveloperRbacService:
    return DeveloperRbacService(repos)


async def get_secret_reference_service(repos: RepositoryRegistry = Depends(get_repos)) -> SecretReferenceService:
    return SecretReferenceService(repos)


async def get_plugin_isolation_service() -> PluginIsolationService:
    return PluginIsolationService()


async def get_oauth_readiness_service() -> OAuthReadinessService:
    return OAuthReadinessService()
