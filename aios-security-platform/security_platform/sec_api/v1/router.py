"""Aggregates every v1 router into one include-able APIRouter."""
from __future__ import annotations

from fastapi import APIRouter

from security_platform.sec_api.v1 import (
    analytics,
    compliance,
    dlp,
    encryption,
    events,
    governance,
    guardrails,
    pii,
    policies,
    risk,
    secrets,
    threats,
)

api_router = APIRouter()
api_router.include_router(policies.router)
api_router.include_router(guardrails.router)
api_router.include_router(pii.router)
api_router.include_router(dlp.router)
api_router.include_router(secrets.router)
api_router.include_router(encryption.router)
api_router.include_router(risk.router)
api_router.include_router(threats.router)
api_router.include_router(governance.router)
api_router.include_router(events.router)
api_router.include_router(events.audit_router)
api_router.include_router(compliance.router)
api_router.include_router(analytics.router)
