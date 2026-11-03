"""MetricScorer: the runtime entry point for computing metrics and,
optionally, recording standalone `MetricResultModel` rows for a subject
that isn't necessarily part of a full evaluation run (e.g. an ad-hoc
score on a single production response). `sync_definitions` upserts the
DB-facing `MetricDefinitionModel` catalog from the in-code
`METRIC_SPECS` registry so a UI can list metrics without importing
Python."""
from __future__ import annotations

from eval_platform.core.exceptions import MetricComputationError
from eval_platform.metrics.inputs import MetricInput
from eval_platform.metrics.registry import METRIC_SPECS, get_metric_spec
from eval_platform.models.metric import MetricDefinitionModel, MetricResultModel
from eval_platform.repositories.registry import RepositoryRegistry


class MetricScorer:
    def __init__(self, repos: RepositoryRegistry | None = None):
        self.repos = repos

    def compute(self, metric_key: str, metric_input: MetricInput) -> float:
        spec = get_metric_spec(metric_key)
        return spec.compute(metric_input)

    def compute_many(self, metric_keys: list[str], metric_input: MetricInput, *, skip_errors: bool = False) -> dict[str, float | None]:
        results: dict[str, float | None] = {}
        for key in metric_keys:
            try:
                results[key] = self.compute(key, metric_input)
            except MetricComputationError:
                if not skip_errors:
                    raise
                results[key] = None
        return results

    async def sync_definitions(self) -> list[MetricDefinitionModel]:
        if self.repos is None:
            raise MetricComputationError("MetricScorer requires a RepositoryRegistry to sync definitions")
        synced = []
        for spec in METRIC_SPECS:
            existing = await self.repos.metric_definitions.get_by_key(spec.key)
            if existing is None:
                existing = await self.repos.metric_definitions.add(MetricDefinitionModel(**spec.as_definition_kwargs()))
            else:
                for field_name, value in spec.as_definition_kwargs().items():
                    setattr(existing, field_name, value)
                existing = await self.repos.metric_definitions.update(existing)
            synced.append(existing)
        return synced

    async def record_result(
        self, workspace_id: str, metric_key: str, *, subject_type: str, subject_id: str | None, metric_input: MetricInput
    ) -> MetricResultModel:
        if self.repos is None:
            raise MetricComputationError("MetricScorer requires a RepositoryRegistry to record results")
        value = self.compute(metric_key, metric_input)
        return await self.repos.metric_results.add(MetricResultModel(
            workspace_id=workspace_id, metric_key=metric_key, subject_type=subject_type, subject_id=subject_id, value=value,
        ))
