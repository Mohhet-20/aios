"""Aggregates every v1 router into one include-able APIRouter."""
from __future__ import annotations

from fastapi import APIRouter

from prompt_platform.prompt_api.v1 import (
    deployment,
    evaluation,
    experiments,
    governance,
    import_export,
    observability,
    optimization,
    prompts,
    security,
    studio,
    testing,
    versions,
    workspaces,
)

api_router = APIRouter()
api_router.include_router(workspaces.router)
api_router.include_router(prompts.router)
api_router.include_router(versions.router)
api_router.include_router(studio.router)
api_router.include_router(testing.router)
api_router.include_router(evaluation.router)
api_router.include_router(optimization.router)
api_router.include_router(experiments.router)
api_router.include_router(deployment.router)
api_router.include_router(observability.router)
api_router.include_router(governance.router)
api_router.include_router(security.router)
api_router.include_router(import_export.router)
