"""Aggregates every v1 router into one include-able APIRouter."""
from __future__ import annotations

from fastapi import APIRouter

from agent_platform.agent_api.v1 import (
    agent_types,
    agents,
    communication,
    governance,
    memory,
    observability,
    orchestration,
    planning,
    reasoning,
    tools,
    workspaces,
)

api_router = APIRouter()
api_router.include_router(workspaces.router)
api_router.include_router(agent_types.router)
api_router.include_router(agents.router)
api_router.include_router(planning.router)
api_router.include_router(orchestration.router)
api_router.include_router(communication.router)
api_router.include_router(reasoning.router)
api_router.include_router(tools.router)
api_router.include_router(memory.router)
api_router.include_router(governance.router)
api_router.include_router(observability.router)
