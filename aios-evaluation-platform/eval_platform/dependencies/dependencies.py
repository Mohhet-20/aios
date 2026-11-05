"""FastAPI dependency wiring: DB session -> RepositoryRegistry -> every
service, plus a minimal caller-identity dependency.

Auth is intentionally minimal here: this platform expects to sit behind
an already-authenticated gateway that forwards the caller's identity via
the `X-User-Id` header — the same seam every sibling AIOS platform uses.
Every router depends on `get_current_actor_id`, never on the header
directly, so swapping in real token validation later is a one-file
change.

Every service is built fresh per request off a per-request
`RepositoryRegistry`/`AsyncSession`, since a session must never be
shared across concurrent requests."""
from __future__ import annotations

from collections.abc import AsyncGenerator

from fastapi import Depends, Header, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from eval_platform.alerting.alert_service import AlertService
from eval_platform.alerting.evaluator import AlertEvaluator
from eval_platform.alerting.rule_service import AlertRuleService
from eval_platform.analytics.improvement_loop import ImprovementLoopService
from eval_platform.analytics.recommendation_service import RecommendationService
from eval_platform.analytics.snapshot_service import AnalyticsSnapshotService
from eval_platform.benchmarking.benchmark_service import BenchmarkService
from eval_platform.benchmarking.run_service import BenchmarkRunService
from eval_platform.config.settings import Settings, get_settings
from eval_platform.database.session import get_db_session
from eval_platform.datasets.dataset_service import DatasetService
from eval_platform.datasets.version_service import DatasetVersionService
from eval_platform.evaluation_core.evaluation_service import EvaluationService
from eval_platform.evaluation_core.version_service import EvaluationVersionService
from eval_platform.execution.evaluation_run_service import EvaluationRunService
from eval_platform.governance.audit_service import AuditService
from eval_platform.governance.policy_service import EvaluationPolicyService
from eval_platform.governance.rbac_service import RBACService
from eval_platform.governance.retention_service import RetentionService
from eval_platform.hallucination.service import HallucinationDetectionService
from eval_platform.metrics.scorer import MetricScorer
from eval_platform.observability.ingestion_service import ObservabilityIngestionService
from eval_platform.observability.monitoring_service import ObservabilityMonitoringService
from eval_platform.repositories.registry import RepositoryRegistry


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    async for session in get_db_session():
        yield session


async def get_repos(session: AsyncSession = Depends(get_session, scope="function")) -> RepositoryRegistry:
    return RepositoryRegistry(session)


def get_settings_dep() -> Settings:
    return get_settings()


async def get_current_actor_id(x_user_id: str | None = Header(default=None)) -> str:
    if not x_user_id:
        raise HTTPException(status_code=401, detail="Missing X-User-Id header")
    return x_user_id


# -- evaluation core -------------------------------------------------------------

def get_evaluation_service(repos: RepositoryRegistry = Depends(get_repos)) -> EvaluationService:
    return EvaluationService(repos)


def get_evaluation_version_service(repos: RepositoryRegistry = Depends(get_repos)) -> EvaluationVersionService:
    return EvaluationVersionService(repos)


def get_evaluation_run_service(repos: RepositoryRegistry = Depends(get_repos)) -> EvaluationRunService:
    return EvaluationRunService(repos)


# -- datasets ----------------------------------------------------------------------

def get_dataset_service(repos: RepositoryRegistry = Depends(get_repos)) -> DatasetService:
    return DatasetService(repos)


def get_dataset_version_service(repos: RepositoryRegistry = Depends(get_repos)) -> DatasetVersionService:
    return DatasetVersionService(repos)


# -- metrics -------------------------------------------------------------------------

def get_metric_scorer(repos: RepositoryRegistry = Depends(get_repos)) -> MetricScorer:
    return MetricScorer(repos)


# -- benchmarking --------------------------------------------------------------------

def get_benchmark_service(repos: RepositoryRegistry = Depends(get_repos)) -> BenchmarkService:
    return BenchmarkService(repos)


def get_benchmark_run_service(repos: RepositoryRegistry = Depends(get_repos)) -> BenchmarkRunService:
    return BenchmarkRunService(repos)


# -- hallucination ---------------------------------------------------------------------

def get_hallucination_service(repos: RepositoryRegistry = Depends(get_repos)) -> HallucinationDetectionService:
    return HallucinationDetectionService(repos)


# -- observability ---------------------------------------------------------------------

def get_observability_ingestion_service(repos: RepositoryRegistry = Depends(get_repos)) -> ObservabilityIngestionService:
    return ObservabilityIngestionService(repos)


def get_observability_monitoring_service(repos: RepositoryRegistry = Depends(get_repos)) -> ObservabilityMonitoringService:
    return ObservabilityMonitoringService(repos)


# -- alerting ------------------------------------------------------------------------

def get_alert_rule_service(repos: RepositoryRegistry = Depends(get_repos)) -> AlertRuleService:
    return AlertRuleService(repos)


def get_alert_service(repos: RepositoryRegistry = Depends(get_repos)) -> AlertService:
    return AlertService(repos)


def get_alert_evaluator(repos: RepositoryRegistry = Depends(get_repos)) -> AlertEvaluator:
    return AlertEvaluator(repos)


# -- analytics / improvement loop -----------------------------------------------------

def get_analytics_snapshot_service(repos: RepositoryRegistry = Depends(get_repos)) -> AnalyticsSnapshotService:
    return AnalyticsSnapshotService(repos)


def get_recommendation_service(repos: RepositoryRegistry = Depends(get_repos)) -> RecommendationService:
    return RecommendationService(repos)


def get_improvement_loop_service(repos: RepositoryRegistry = Depends(get_repos)) -> ImprovementLoopService:
    return ImprovementLoopService(repos)


# -- governance ------------------------------------------------------------------------

def get_rbac_service(repos: RepositoryRegistry = Depends(get_repos)) -> RBACService:
    return RBACService(repos)


def get_audit_service(repos: RepositoryRegistry = Depends(get_repos)) -> AuditService:
    return AuditService(repos)


def get_policy_service(repos: RepositoryRegistry = Depends(get_repos)) -> EvaluationPolicyService:
    return EvaluationPolicyService(repos)


def get_retention_service(repos: RepositoryRegistry = Depends(get_repos)) -> RetentionService:
    return RetentionService(repos)
