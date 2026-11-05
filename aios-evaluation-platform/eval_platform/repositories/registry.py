"""RepositoryRegistry: wires every repository to one shared AsyncSession,
so a single unit-of-work-scoped session backs every repository an
application-service call touches. Same pattern as every other AIOS
services's `RepositoryRegistry`."""
from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from eval_platform.repositories.alert_repository import AlertRepository, AlertRuleRepository
from eval_platform.repositories.analytics_repository import AnalyticsSnapshotRepository, RecommendationRepository
from eval_platform.repositories.benchmark_repository import (
    BenchmarkCandidateResultRepository,
    BenchmarkRepository,
    BenchmarkRunRepository,
)
from eval_platform.repositories.dataset_repository import (
    DatasetItemRepository,
    DatasetRepository,
    DatasetVersionRepository,
)
from eval_platform.repositories.evaluation_repository import EvaluationRepository, EvaluationVersionRepository
from eval_platform.repositories.governance_repository import AuditLogEntryRepository, PermissionGrantRepository
from eval_platform.repositories.hallucination_repository import HallucinationCheckRepository
from eval_platform.repositories.metric_repository import MetricDefinitionRepository, MetricResultRepository
from eval_platform.repositories.observability_repository import ObservabilityEventRepository
from eval_platform.repositories.run_repository import EvaluationItemResultRepository, EvaluationRunRepository
from eval_platform.repositories.workspace_repository import WorkspaceRepository


class RepositoryRegistry:
    """One instance per unit-of-work session; exposes every repository as
    a lazily-constructed, memoized property so services only pay for the
    repositories they actually touch."""

    def __init__(self, session: AsyncSession):
        self.session = session
        self._cache: dict[str, object] = {}

    def _get(self, key: str, cls: type):
        if key not in self._cache:
            self._cache[key] = cls(self.session)
        return self._cache[key]

    @property
    def workspaces(self) -> WorkspaceRepository:
        return self._get("workspaces", WorkspaceRepository)

    @property
    def evaluations(self) -> EvaluationRepository:
        return self._get("evaluations", EvaluationRepository)

    @property
    def evaluation_versions(self) -> EvaluationVersionRepository:
        return self._get("evaluation_versions", EvaluationVersionRepository)

    @property
    def evaluation_runs(self) -> EvaluationRunRepository:
        return self._get("evaluation_runs", EvaluationRunRepository)

    @property
    def evaluation_item_results(self) -> EvaluationItemResultRepository:
        return self._get("evaluation_item_results", EvaluationItemResultRepository)

    @property
    def datasets(self) -> DatasetRepository:
        return self._get("datasets", DatasetRepository)

    @property
    def dataset_versions(self) -> DatasetVersionRepository:
        return self._get("dataset_versions", DatasetVersionRepository)

    @property
    def dataset_items(self) -> DatasetItemRepository:
        return self._get("dataset_items", DatasetItemRepository)

    @property
    def benchmarks(self) -> BenchmarkRepository:
        return self._get("benchmarks", BenchmarkRepository)

    @property
    def benchmark_runs(self) -> BenchmarkRunRepository:
        return self._get("benchmark_runs", BenchmarkRunRepository)

    @property
    def benchmark_candidate_results(self) -> BenchmarkCandidateResultRepository:
        return self._get("benchmark_candidate_results", BenchmarkCandidateResultRepository)

    @property
    def metric_definitions(self) -> MetricDefinitionRepository:
        return self._get("metric_definitions", MetricDefinitionRepository)

    @property
    def metric_results(self) -> MetricResultRepository:
        return self._get("metric_results", MetricResultRepository)

    @property
    def hallucination_checks(self) -> HallucinationCheckRepository:
        return self._get("hallucination_checks", HallucinationCheckRepository)

    @property
    def observability_events(self) -> ObservabilityEventRepository:
        return self._get("observability_events", ObservabilityEventRepository)

    @property
    def alert_rules(self) -> AlertRuleRepository:
        return self._get("alert_rules", AlertRuleRepository)

    @property
    def alerts(self) -> AlertRepository:
        return self._get("alerts", AlertRepository)

    @property
    def analytics_snapshots(self) -> AnalyticsSnapshotRepository:
        return self._get("analytics_snapshots", AnalyticsSnapshotRepository)

    @property
    def recommendations(self) -> RecommendationRepository:
        return self._get("recommendations", RecommendationRepository)

    @property
    def permission_grants(self) -> PermissionGrantRepository:
        return self._get("permission_grants", PermissionGrantRepository)

    @property
    def audit_log(self) -> AuditLogEntryRepository:
        return self._get("audit_log", AuditLogEntryRepository)
