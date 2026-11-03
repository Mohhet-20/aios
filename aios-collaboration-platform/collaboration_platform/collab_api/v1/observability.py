"""Observability: collaboration activity, workspace usage, editing
sessions, review metrics, notification delivery, engagement, growth."""
from __future__ import annotations

from fastapi import APIRouter, Depends

from collaboration_platform.analytics.observability_service import ObservabilityService
from collaboration_platform.dependencies.dependencies import get_observability_service

router = APIRouter(prefix="/observability", tags=["observability"])


@router.get("/workspace/{workspace_id}/activity-summary")
async def activity_summary(workspace_id: str, service: ObservabilityService = Depends(get_observability_service)):
    return await service.collaboration_activity_summary(workspace_id)


@router.get("/workspace/{workspace_id}/usage")
async def workspace_usage(workspace_id: str, service: ObservabilityService = Depends(get_observability_service)):
    return await service.workspace_usage(workspace_id)


@router.get("/asset/{asset_id}/editing-sessions")
async def editing_session_stats(asset_id: str, service: ObservabilityService = Depends(get_observability_service)):
    return await service.editing_session_stats(asset_id)


@router.get("/workspace/{workspace_id}/review-metrics")
async def review_metrics(workspace_id: str, service: ObservabilityService = Depends(get_observability_service)):
    return await service.review_metrics(workspace_id)


@router.get("/user/{recipient_id}/notification-delivery")
async def notification_delivery_stats(recipient_id: str, service: ObservabilityService = Depends(get_observability_service)):
    return await service.notification_delivery_stats(recipient_id)


@router.get("/user/{user_id}/engagement")
async def user_engagement(user_id: str, service: ObservabilityService = Depends(get_observability_service)):
    return await service.user_engagement(user_id)


@router.get("/workspace/{workspace_id}/growth")
async def workspace_growth(workspace_id: str, service: ObservabilityService = Depends(get_observability_service)):
    return await service.workspace_growth(workspace_id)
