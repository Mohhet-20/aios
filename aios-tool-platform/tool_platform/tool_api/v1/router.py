"""Aggregates every v1 router into one include-able APIRouter."""
from __future__ import annotations

from fastapi import APIRouter

from tool_platform.tool_api.v1 import (
    credentials,
    execution,
    governance,
    installations,
    marketplace,
    observability,
    planning,
    plugins,
    registry,
    scheduling,
    tools,
    versions,
    workspaces,
)

api_router = APIRouter()
api_router.include_router(workspaces.router)
api_router.include_router(tools.router)
api_router.include_router(versions.router)
api_router.include_router(registry.router)
api_router.include_router(plugins.router)
api_router.include_router(installations.router)
api_router.include_router(marketplace.router)
api_router.include_router(credentials.router)
api_router.include_router(execution.router)
api_router.include_router(planning.router)
api_router.include_router(scheduling.router)
api_router.include_router(observability.router)
api_router.include_router(governance.router)
