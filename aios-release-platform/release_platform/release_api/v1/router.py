"""Aggregates every v1 router (health is mounted separately at the
app root, not under /api/v1) into one include-able APIRouter."""
from __future__ import annotations

from fastapi import APIRouter

from release_platform.release_api.v1 import (
    analytics,
    artifact_distribution,
    deployment,
    environments,
    feature_flags,
    licensing,
    release_versioning,
    rollback,
    rollouts,
    security,
    updates,
    validation,
)

api_router = APIRouter()

api_router.include_router(release_versioning.router)
api_router.include_router(release_versioning.compatibility_router)

api_router.include_router(artifact_distribution.router)
api_router.include_router(artifact_distribution.channels_router)
api_router.include_router(artifact_distribution.entries_router)

api_router.include_router(deployment.router)

api_router.include_router(rollouts.router)

api_router.include_router(feature_flags.router)
api_router.include_router(feature_flags.overrides_router)

api_router.include_router(updates.router)

api_router.include_router(licensing.router)

api_router.include_router(environments.router)

api_router.include_router(validation.router)

api_router.include_router(rollback.router)

api_router.include_router(security.router)
api_router.include_router(security.signatures_router)
api_router.include_router(security.approvals_router)

api_router.include_router(analytics.router)
api_router.include_router(analytics.adoption_router)
