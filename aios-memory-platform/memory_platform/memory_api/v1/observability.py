"""Observability & Analytics: retrieval latency/quality/failure-rate
rollups, context-assembly performance, embedding index health, memory
reads/writes, knowledge growth, storage usage, and per-agent memory
usage — the Memory Analytics / Retrieval Performance dashboard surfaces."""
from __future__ import annotations

from dataclasses import asdict
from datetime import datetime

from fastapi import APIRouter, Depends

from memory_platform.analytics.analytics_service import AnalyticsService
from memory_platform.memory_api.dependencies import get_analytics_service

router = APIRouter(prefix="/workspaces/{workspace_id}/analytics", tags=["observability"])


@router.get("/retrieval-performance")
async def retrieval_performance(workspace_id: str, since: datetime | None = None, svc: AnalyticsService = Depends(get_analytics_service)):
    return asdict(await svc.retrieval_performance(workspace_id, since=since))


@router.get("/context-assembly-performance")
async def context_assembly_performance(workspace_id: str, svc: AnalyticsService = Depends(get_analytics_service)):
    return asdict(await svc.context_assembly_performance(workspace_id))


@router.get("/embedding-performance")
async def embedding_performance(workspace_id: str, svc: AnalyticsService = Depends(get_analytics_service)):
    return asdict(await svc.embedding_performance(workspace_id))


@router.get("/memory")
async def memory_analytics(workspace_id: str, window_days: int = 30, svc: AnalyticsService = Depends(get_analytics_service)):
    return asdict(await svc.memory_analytics(workspace_id, window_days=window_days))


@router.get("/knowledge-growth")
async def knowledge_growth(workspace_id: str, window_days: int = 30, svc: AnalyticsService = Depends(get_analytics_service)):
    return asdict(await svc.knowledge_growth(workspace_id, window_days=window_days))


@router.get("/storage-usage")
async def storage_usage(workspace_id: str, svc: AnalyticsService = Depends(get_analytics_service)):
    return asdict(await svc.storage_usage(workspace_id))


@router.get("/agent-memory-usage")
async def agent_memory_usage(workspace_id: str, svc: AnalyticsService = Depends(get_analytics_service)):
    return [asdict(u) for u in await svc.agent_memory_usage(workspace_id)]
