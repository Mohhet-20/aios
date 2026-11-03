"""Chaos experiment job lifecycle: request_experiment() enqueues a
failure-injection experiment against one of the twelve failure types,
rejecting anything whose requested blast radius exceeds the
platform-wide `chaos_max_blast_radius_pct` safety cap before a single
statement is committed. start()/complete()/fail() drive the guarded
queued -> running -> completed/failed transitions on the domain-level
`ChaosExperiment` entity, and finish_experiment() is the convenience
orchestrator that records the recovery outcome (whether the target
came back, and how long it took) alongside completion."""
from __future__ import annotations


from quality_platform.config.settings import get_settings
from quality_platform.core.exceptions import (
    BlastRadiusExceededError,
    ChaosExperimentNotFoundError,
    InvalidTransitionError,
    UnsupportedFailureTypeError,
)
from quality_platform.domain.entities import ChaosExperiment
from quality_platform.domain.enums import JobStatus
from quality_platform.models.chaos import ChaosExperimentModel
from quality_platform.repositories.registry import RepositoryRegistry
from quality_platform.clock import utc_now


class ChaosExperimentService:
    def __init__(self, repos: RepositoryRegistry):
        self.repos = repos
        self.settings = get_settings()

    async def get_or_404(self, tenant_id: str, experiment_id: str) -> ChaosExperimentModel:
        experiment = await self.repos.chaos_experiments.get_or_404(experiment_id)
        if experiment.tenant_id != tenant_id:
            raise ChaosExperimentNotFoundError(f"Chaos experiment '{experiment_id}' not found for tenant '{tenant_id}'")
        return experiment

    async def request_experiment(
        self, tenant_id: str, *, failure_type: str, target_ref: str, blast_radius_pct: float, config: dict | None = None
    ) -> ChaosExperimentModel:
        if failure_type not in self.settings.chaos_failure_types:
            raise UnsupportedFailureTypeError(f"Unsupported chaos failure type '{failure_type}'")
        if blast_radius_pct > self.settings.chaos_max_blast_radius_pct:
            raise BlastRadiusExceededError(
                f"Requested blast radius {blast_radius_pct}% exceeds the platform cap of "
                f"{self.settings.chaos_max_blast_radius_pct}%"
            )
        experiment = ChaosExperimentModel(
            tenant_id=tenant_id, failure_type=failure_type, target_ref=target_ref,
            blast_radius_pct=blast_radius_pct, config=config or {}, status=JobStatus.QUEUED.value,
        )
        return await self.repos.chaos_experiments.add(experiment)

    async def _apply_transition(self, tenant_id: str, experiment_id: str, transition_name: str) -> ChaosExperimentModel:
        experiment = await self.get_or_404(tenant_id, experiment_id)
        entity = ChaosExperiment(id=experiment.id, status=JobStatus(experiment.status))
        try:
            getattr(entity, transition_name)()
        except InvalidTransitionError:
            raise
        experiment.status = entity.status.value
        return experiment

    async def start(self, tenant_id: str, experiment_id: str) -> ChaosExperimentModel:
        experiment = await self._apply_transition(tenant_id, experiment_id, "start")
        return await self.repos.chaos_experiments.update(experiment)

    async def complete(
        self, tenant_id: str, experiment_id: str, *, result: dict, recovered: bool | None, recovery_time_seconds: float | None
    ) -> ChaosExperimentModel:
        experiment = await self._apply_transition(tenant_id, experiment_id, "complete")
        experiment.result = result
        experiment.recovered = recovered
        experiment.recovery_time_seconds = recovery_time_seconds
        experiment.completed_at = utc_now()
        return await self.repos.chaos_experiments.update(experiment)

    async def fail(self, tenant_id: str, experiment_id: str, *, error: str) -> ChaosExperimentModel:
        experiment = await self._apply_transition(tenant_id, experiment_id, "fail")
        experiment.error = error
        experiment.completed_at = utc_now()
        return await self.repos.chaos_experiments.update(experiment)

    async def finish_experiment(
        self, tenant_id: str, experiment_id: str, *, recovered: bool, recovery_time_seconds: float | None = None
    ) -> ChaosExperimentModel:
        result = {"recovered": recovered, "recovery_time_seconds": recovery_time_seconds}
        return await self.complete(
            tenant_id, experiment_id, result=result, recovered=recovered, recovery_time_seconds=recovery_time_seconds
        )

    async def list_experiments(self, tenant_id: str, *, failure_type: str | None = None, limit: int = 100) -> list[ChaosExperimentModel]:
        return await self.repos.chaos_experiments.list_for_tenant(tenant_id, failure_type=failure_type, limit=limit)
