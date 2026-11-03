"""Experiment tracking: experiments group runs; runs carry a guarded
running -> completed/failed/killed lifecycle; metrics support
multi-step logging (training curves), parameters are logged once per
key per run (the reproducibility record of what config produced a
result); `compare_runs` reads the latest value of a metric key across
a set of runs side by side, the read-only comparison view the Model
Lifecycle module's promotion decisions and the Evaluation Platform's
benchmarking would draw on."""
from __future__ import annotations

from datetime import timezone

from infra_platform.config.settings import Settings, get_settings
from infra_platform.core.exceptions import ExperimentError, NotFoundError, RunAlreadyFinishedError, RunNotFoundError
from infra_platform.domain.entities import ExperimentRun as ExperimentRunEntity
from infra_platform.domain.enums import RunStatus
from infra_platform.models.experiments import ExperimentModel, ExperimentRunModel, RunMetricModel, RunParamModel
from infra_platform.repositories.registry import RepositoryRegistry
from infra_platform.clock import utc_now


def _to_run_entity(model: ExperimentRunModel) -> ExperimentRunEntity:
    return ExperimentRunEntity(id=model.id, status=RunStatus(model.status))


class ExperimentService:
    def __init__(self, repos: RepositoryRegistry):
        self.repos = repos

    async def create_experiment(
        self, tenant_id: str, *, name: str, description: str | None = None, owner_id: str | None = None
    ) -> ExperimentModel:
        existing = await self.repos.experiments.get_by_name(tenant_id, name)
        if existing is not None:
            raise ExperimentError(f"Experiment '{name}' already exists")
        experiment = ExperimentModel(tenant_id=tenant_id, name=name, description=description, owner_id=owner_id)
        return await self.repos.experiments.add(experiment)

    async def get(self, tenant_id: str, experiment_id: str) -> ExperimentModel:
        experiment = await self.repos.experiments.get(experiment_id)
        if experiment is None or experiment.tenant_id != tenant_id:
            raise NotFoundError(f"Experiment '{experiment_id}' not found")
        return experiment

    async def list_for_tenant(self, tenant_id: str) -> list[ExperimentModel]:
        return await self.repos.experiments.list_for_tenant(tenant_id)


class ExperimentRunService:
    def __init__(self, repos: RepositoryRegistry, *, settings: Settings | None = None):
        self.repos = repos
        self.settings = settings or get_settings()

    async def start_run(
        self, tenant_id: str, experiment_id: str, *, run_name: str | None = None, source: str | None = None
    ) -> ExperimentRunModel:
        experiment = await self.repos.experiments.get(experiment_id)
        if experiment is None or experiment.tenant_id != tenant_id:
            raise NotFoundError(f"Experiment '{experiment_id}' not found")
        run = ExperimentRunModel(
            tenant_id=tenant_id, experiment_id=experiment_id, run_name=run_name,
            status=RunStatus.RUNNING.value, source=source,
        )
        return await self.repos.experiment_runs.add(run)

    async def _get_run(self, tenant_id: str, run_id: str) -> ExperimentRunModel:
        run = await self.repos.experiment_runs.get(run_id)
        if run is None or run.tenant_id != tenant_id:
            raise RunNotFoundError(f"ExperimentRun '{run_id}' not found")
        return run

    async def _transition(self, tenant_id: str, run_id: str, action: str) -> ExperimentRunModel:
        run = await self._get_run(tenant_id, run_id)
        entity = _to_run_entity(run)
        getattr(entity, action)()
        run.status = entity.status.value
        run.finished_at = entity.finished_at
        return await self.repos.experiment_runs.update(run)

    async def complete_run(self, tenant_id: str, run_id: str) -> ExperimentRunModel:
        return await self._transition(tenant_id, run_id, "complete")

    async def fail_run(self, tenant_id: str, run_id: str) -> ExperimentRunModel:
        return await self._transition(tenant_id, run_id, "fail")

    async def kill_run(self, tenant_id: str, run_id: str) -> ExperimentRunModel:
        return await self._transition(tenant_id, run_id, "kill")

    async def log_metric(self, tenant_id: str, run_id: str, *, key: str, value: float, step: int = 0) -> RunMetricModel:
        run = await self._get_run(tenant_id, run_id)
        if run.status != RunStatus.RUNNING.value:
            raise RunAlreadyFinishedError(f"Run '{run_id}' is {run.status}; cannot log further metrics")
        metric = RunMetricModel(tenant_id=tenant_id, run_id=run_id, key=key, value=value, step=step)
        return await self.repos.run_metrics.add(metric)

    async def log_param(self, tenant_id: str, run_id: str, *, key: str, value: str) -> RunParamModel:
        run = await self._get_run(tenant_id, run_id)
        if run.status != RunStatus.RUNNING.value:
            raise RunAlreadyFinishedError(f"Run '{run_id}' is {run.status}; cannot log further parameters")
        existing = await self.repos.run_params.list_for_run(tenant_id, run_id)
        if any(p.key == key for p in existing):
            raise ExperimentError(f"Parameter '{key}' already logged for run '{run_id}'")
        param = RunParamModel(tenant_id=tenant_id, run_id=run_id, key=key, value=value)
        return await self.repos.run_params.add(param)

    async def get_metrics(self, tenant_id: str, run_id: str, *, key: str | None = None) -> list[RunMetricModel]:
        if key is not None:
            return await self.repos.run_metrics.list_for_run_key(tenant_id, run_id, key)
        return await self.repos.run_metrics.list_for_run(tenant_id, run_id)

    async def get_params(self, tenant_id: str, run_id: str) -> list[RunParamModel]:
        return await self.repos.run_params.list_for_run(tenant_id, run_id)

    async def list_for_experiment(self, tenant_id: str, experiment_id: str) -> list[ExperimentRunModel]:
        return await self.repos.experiment_runs.list_for_experiment(tenant_id, experiment_id)

    async def compare_runs(self, tenant_id: str, run_ids: list[str], *, metric_key: str) -> dict[str, float | None]:
        """Latest logged value of `metric_key` per run, `None` if the
        run never logged that key — the side-by-side comparison a
        promotion or benchmarking decision would be made from."""
        comparison: dict[str, float | None] = {}
        for run_id in run_ids:
            await self._get_run(tenant_id, run_id)
            history = await self.repos.run_metrics.list_for_run_key(tenant_id, run_id, metric_key)
            comparison[run_id] = history[-1].value if history else None
        return comparison

    async def prune_stale_metrics(self, tenant_id: str, run_id: str) -> int:
        """Deletes metric rows older than `experiment_metric_retention_days`
        for a run — a bounded-growth sweep for long-lived training
        curves, mirroring the retention posture used across the platform."""
        cutoff = utc_now().timestamp() - self.settings.experiment_metric_retention_days * 86400
        metrics = await self.repos.run_metrics.list_for_run(tenant_id, run_id)
        pruned = 0
        for metric in metrics:
            logged_at = metric.logged_at
            if logged_at.tzinfo is None:
                logged_at = logged_at.replace(tzinfo=timezone.utc)
            if logged_at.timestamp() < cutoff:
                await self.repos.run_metrics.delete(metric)
                pruned += 1
        return pruned
