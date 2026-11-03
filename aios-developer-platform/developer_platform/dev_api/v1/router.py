"""Aggregates every v1 router (health is mounted separately at the
app root, not under /api/v1) into one include-able APIRouter."""
from __future__ import annotations

from fastapi import APIRouter

from developer_platform.dev_api.v1 import (
    api_platform,
    cli_platform,
    codegen,
    dev_security,
    developer_analytics,
    developer_portal,
    extension_framework,
    mcp_integration,
    plugin_sdk,
    registry_platform,
    sdk_platform,
    webhook_platform,
)

api_router = APIRouter()

api_router.include_router(api_platform.router)
api_router.include_router(api_platform.usage_router)
api_router.include_router(api_platform.versions_router)

api_router.include_router(sdk_platform.router)
api_router.include_router(sdk_platform.packages_router)

api_router.include_router(cli_platform.router)
api_router.include_router(cli_platform.commands_router)

api_router.include_router(plugin_sdk.router)
api_router.include_router(plugin_sdk.marketplace_router)

api_router.include_router(extension_framework.router)
api_router.include_router(extension_framework.registrations_router)

api_router.include_router(webhook_platform.router)
api_router.include_router(webhook_platform.deliveries_router)

api_router.include_router(mcp_integration.router)
api_router.include_router(mcp_integration.sessions_router)

api_router.include_router(codegen.router)

api_router.include_router(developer_portal.router)
api_router.include_router(developer_portal.sandbox_router)

api_router.include_router(registry_platform.router)

api_router.include_router(developer_analytics.router)
api_router.include_router(developer_analytics.dashboard_router)

api_router.include_router(dev_security.router)
api_router.include_router(dev_security.secrets_router)
api_router.include_router(dev_security.isolation_router)
api_router.include_router(dev_security.oauth_router)
