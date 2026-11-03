"""Aggregates every v1 router into one include-able APIRouter."""
from __future__ import annotations

from fastapi import APIRouter

from identity_platform.identity_api.v1 import (
    api_keys,
    authorization,
    auth,
    federated,
    governance,
    groups,
    invitations,
    memberships,
    mfa,
    observability,
    organizations,
    projects,
    security,
    sessions,
    teams,
    tenancy,
    workspaces,
)

api_router = APIRouter()
api_router.include_router(auth.router)
api_router.include_router(mfa.router)
api_router.include_router(sessions.router)
api_router.include_router(federated.router)
api_router.include_router(authorization.router)
api_router.include_router(organizations.router)
api_router.include_router(workspaces.router)
api_router.include_router(teams.router)
api_router.include_router(projects.router)
api_router.include_router(groups.router)
api_router.include_router(memberships.router)
api_router.include_router(invitations.router)
api_router.include_router(tenancy.router)
api_router.include_router(api_keys.router)
api_router.include_router(security.router)
api_router.include_router(governance.router)
api_router.include_router(observability.router)
