"""Aggregates every v1 router into one include-able APIRouter."""
from __future__ import annotations

from fastapi import APIRouter

from collaboration_platform.collab_api.v1 import (
    activity,
    assets,
    comments,
    governance,
    libraries,
    notifications,
    observability,
    productivity,
    projects,
    realtime,
    reviews,
    search,
    versions,
    workspaces,
)

api_router = APIRouter()
api_router.include_router(workspaces.router)
api_router.include_router(projects.router)
api_router.include_router(projects.folders_router)
api_router.include_router(projects.collections_router)
api_router.include_router(projects.tags_router)
api_router.include_router(projects.favorites_router)
api_router.include_router(assets.router)
api_router.include_router(realtime.router)
api_router.include_router(comments.router)
api_router.include_router(activity.router)
api_router.include_router(notifications.router)
api_router.include_router(versions.router)
api_router.include_router(versions.branches_router)
api_router.include_router(reviews.router)
api_router.include_router(reviews.policies_router)
api_router.include_router(libraries.router)
api_router.include_router(search.router)
api_router.include_router(productivity.router)
api_router.include_router(productivity.checklists_router)
api_router.include_router(productivity.bookmarks_router)
api_router.include_router(productivity.pinned_router)
api_router.include_router(observability.router)
api_router.include_router(governance.router)
