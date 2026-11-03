"""FastAPI dependency wiring: DB session -> RepositoryRegistry ->
every service. Auth is intentionally minimal here, matching every
sibling AIOS platform: this platform expects to sit behind an
already-authenticated gateway (in practice, the Identity Platform)
that forwards the caller's tenant via `X-Tenant-Id` and, where
relevant, the acting principal via `X-User-Id`. Every service is
built fresh per request off a per-request `RepositoryRegistry`/
`AsyncSession`, since a session must never be shared across
concurrent requests."""
from __future__ import annotations

from collections.abc import AsyncGenerator

from fastapi import Depends, Header, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from perf_platform.caching.cache_service import CacheService
from perf_platform.config.settings import Settings, get_settings
from perf_platform.cost_intelligence.cost_service import BudgetService, CostRecordService
from perf_platform.database.session import session_scope
from perf_platform.observability.observability_service import (
    BenchmarkService,
    LatencyTrackingService,
    ThroughputTrackingService,
)
from perf_platform.optimization.optimization_service import RecommendationService
from perf_platform.repositories.registry import RepositoryRegistry
from perf_platform.routing.routing_service import ModelRoutingService, RoutingPolicyService
from perf_platform.scalability.gpu_service import GpuPoolService


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    async for session in session_scope():
        yield session


async def get_repos(session: AsyncSession = Depends(get_session)) -> RepositoryRegistry:
    return RepositoryRegistry(session)


def get_settings_dep() -> Settings:
    return get_settings()


async def get_current_tenant_id(x_tenant_id: str | None = Header(default=None)) -> str:
    if not x_tenant_id:
        raise HTTPException(status_code=400, detail="Missing X-Tenant-Id header")
    return x_tenant_id


async def get_current_actor_id(x_user_id: str | None = Header(default=None)) -> str | None:
    """Unlike the tenant header, the actor header is optional — some of
    what this platform tracks (scheduled benchmark sweeps, automated
    routing decisions) legitimately comes from a process with no human
    actor behind it."""
    return x_user_id


# -- cache platform --
async def get_cache_service(repos: RepositoryRegistry = Depends(get_repos)) -> CacheService:
    return CacheService(repos)


# -- model routing / LLM cost intelligence --
async def get_routing_policy_service(repos: RepositoryRegistry = Depends(get_repos)) -> RoutingPolicyService:
    return RoutingPolicyService(repos)


async def get_model_routing_service(repos: RepositoryRegistry = Depends(get_repos)) -> ModelRoutingService:
    return ModelRoutingService(repos)


# -- cost intelligence engine --
async def get_cost_record_service(repos: RepositoryRegistry = Depends(get_repos)) -> CostRecordService:
    return CostRecordService(repos)


async def get_budget_service(repos: RepositoryRegistry = Depends(get_repos)) -> BudgetService:
    return BudgetService(repos)


# -- auto-optimization engine --
async def get_recommendation_service(repos: RepositoryRegistry = Depends(get_repos)) -> RecommendationService:
    return RecommendationService(repos)


# -- observability & benchmarking --
async def get_latency_service(repos: RepositoryRegistry = Depends(get_repos)) -> LatencyTrackingService:
    return LatencyTrackingService(repos)


async def get_throughput_service(repos: RepositoryRegistry = Depends(get_repos)) -> ThroughputTrackingService:
    return ThroughputTrackingService(repos)


async def get_benchmark_service(repos: RepositoryRegistry = Depends(get_repos)) -> BenchmarkService:
    return BenchmarkService(repos)


# -- GPU / scalability --
async def get_gpu_pool_service(repos: RepositoryRegistry = Depends(get_repos)) -> GpuPoolService:
    return GpuPoolService(repos)
