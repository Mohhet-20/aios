"""Aggregates every v1 router (health is mounted separately at the
app root, not under /api/v1) into one include-able APIRouter."""
from __future__ import annotations

from fastapi import APIRouter

from docs_platform.doc_api.v1 import (
    analytics,
    api_sdk_docs,
    architecture,
    assistant,
    collaboration,
    documentation,
    knowledge,
    learning,
    search,
    security,
    versioning,
)

api_router = APIRouter()

api_router.include_router(documentation.router)
api_router.include_router(documentation.pages_router)

api_router.include_router(api_sdk_docs.router)
api_router.include_router(api_sdk_docs.sdk_router)
api_router.include_router(api_sdk_docs.jobs_router)

api_router.include_router(architecture.router)
api_router.include_router(architecture.tech_stack_router)

api_router.include_router(knowledge.router)

api_router.include_router(learning.router)
api_router.include_router(learning.paths_router)
api_router.include_router(learning.enrollments_router)

api_router.include_router(assistant.router)

api_router.include_router(search.router)

api_router.include_router(versioning.router)
api_router.include_router(versioning.release_notes_router)
api_router.include_router(versioning.deprecations_router)

api_router.include_router(collaboration.router)
api_router.include_router(collaboration.reviews_router)
api_router.include_router(collaboration.audit_router)

api_router.include_router(analytics.router)
api_router.include_router(analytics.feedback_router)
api_router.include_router(analytics.broken_links_router)

api_router.include_router(security.router)
api_router.include_router(security.visibility_router)
api_router.include_router(security.governance_router)
