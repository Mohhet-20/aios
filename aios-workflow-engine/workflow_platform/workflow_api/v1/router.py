"""Aggregates every v1 router into one include-able APIRouter."""
from __future__ import annotations

from fastapi import APIRouter

from workflow_platform.workflow_api.v1 import (
    approvals,
    events,
    execution,
    governance,
    observability,
    scheduling,
    state,
    versions,
    workflows,
    workspaces,
)

api_router = APIRouter()
api_router.include_router(workspaces.router)
api_router.include_router(workflows.router)
api_router.include_router(versions.router)
api_router.include_router(execution.router)
api_router.include_router(scheduling.router)
api_router.include_router(approvals.router)
api_router.include_router(events.router)
api_router.include_router(state.router)
api_router.include_router(observability.router)
api_router.include_router(governance.router)
