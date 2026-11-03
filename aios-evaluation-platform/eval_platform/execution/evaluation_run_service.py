"""EvaluationRunService: executes one EvaluationVersion's target
against every item in its bound dataset's published version, scores
each item via `MetricScorer`, persists per-item detail
(`EvaluationItemResultModel`), and rolls the run up into
`EvaluationRunModel`'s aggregate score — the "did this evaluation pass
overall" view a dashboard renders next to "which specific inputs failed
and why" (the item results). Reuses `_RunMixin`'s shared state machine
from `domain/entities.py` for start/succeed/fail transitions."""
from __future__ import annotations

from eval_platform.core.exceptions import DatasetError, ValidationError
from eval_platform.domain.entities import EvaluationRun
from eval_platform.domain.enums import RunStatus
from eval_platform.execution.executor import TargetExecutor
from eval_platform.metrics.inputs import MetricInput
from eval_platform.metrics.scorer import MetricScorer
from eval_platform.models.evaluation import EvaluationVersionModel
from eval_platform.models.run import EvaluationItemResultModel, EvaluationRunModel
from eval_platform.repositories.registry import RepositoryRegistry


def _run_to_domain(model: EvaluationRunModel) -> EvaluationRun:
    return EvaluationRun(
        id=model.id, evaluation_id=model.evaluation_id, evaluation_version_id=model.evaluation_version_id,
        workspace_id=model.workspace_id, status=RunStatus(model.status), attempt_number=model.attempt_number,
        max_retries=model.max_retries, item_count=model.item_count, passed_count=model.passed_count,
        failed_count=model.failed_count, overall_score=model.overall_score, metric_summary=dict(model.metric_summary or {}),
        error_message=model.error_message, started_at=model.started_at, completed_at=model.completed_at,
        duration_ms=model.duration_ms,
    )


def _apply_run_to_model(entity: EvaluationRun, model: EvaluationRunModel) -> None:
    model.status = entity.status.value
    model.attempt_number = entity.attempt_number
    model.item_count = entity.item_count
    model.passed_count = entity.passed_count
    model.failed_count = entity.failed_count
    model.overall_score = entity.overall_score
    model.metric_summary = entity.metric_summary
    model.error_message = entity.error_message
    model.started_at = entity.started_at
    model.completed_at = entity.completed_at
    model.duration_ms = entity.duration_ms


class EvaluationRunService:
    def __init__(self, repos: RepositoryRegistry):
        self.repos = repos
        self.scorer = MetricScorer(repos)

    async def start_run(
        self, evaluation_id: str, *, triggered_by: str | None = None, trigger_type: str = "manual",
        max_retries: int = 0, timeout_seconds: int = 120,
    ) -> EvaluationRunModel:
        evaluation = await self.repos.evaluations.get_or_404(evaluation_id)
        if not evaluation.current_version_id:
            raise ValidationError(f"evaluation '{evaluation_id}' has no published version to run")
        return await self.repos.evaluation_runs.add(EvaluationRunModel(
            evaluation_id=evaluation_id, evaluation_version_id=evaluation.current_version_id,
            workspace_id=evaluation.workspace_id, triggered_by=triggered_by, trigger_type=trigger_type,
            max_retries=max_retries, timeout_seconds=timeout_seconds,
        ))

    async def get_run(self, run_id: str) -> EvaluationRunModel:
        return await self.repos.evaluation_runs.get_or_404(run_id)

    async def list_runs(self, evaluation_id: str) -> list[EvaluationRunModel]:
        return await self.repos.evaluation_runs.list_for_evaluation(evaluation_id)

    async def list_item_results(self, run_id: str) -> list[EvaluationItemResultModel]:
        return await self.repos.evaluation_item_results.list_for_run(run_id)

    async def execute_run(self, run_id: str, executor: TargetExecutor) -> EvaluationRunModel:
        model = await self.repos.evaluation_runs.get_or_404(run_id)
        entity = _run_to_domain(model)
        entity.start()
        _apply_run_to_model(entity, model)
        model = await self.repos.evaluation_runs.update(model)

        version = await self.repos.evaluation_versions.get_or_404(model.evaluation_version_id)
        try:
            items = await self._load_items(version.dataset_id)
            passed_count = 0
            metric_totals: dict[str, list[float]] = {}
            for item in items:
                result_model = await self._score_item(model.id, version, item, executor)
                if result_model.passed:
                    passed_count += 1
                for key, value in result_model.metric_results.items():
                    if value is not None:
                        metric_totals.setdefault(key, []).append(value)

            metric_summary = {key: sum(values) / len(values) for key, values in metric_totals.items()}
            overall_score = (sum(metric_summary.values()) / len(metric_summary)) if metric_summary else None

            entity = _run_to_domain(model)
            entity.record_results(item_count=len(items), passed_count=passed_count, overall_score=overall_score, metric_summary=metric_summary)
            entity.succeed()
            _apply_run_to_model(entity, model)
            return await self.repos.evaluation_runs.update(model)
        except Exception as exc:
            entity = _run_to_domain(model)
            entity.fail(str(exc))
            _apply_run_to_model(entity, model)
            await self.repos.evaluation_runs.update(model)
            raise

    async def _load_items(self, dataset_id: str | None):
        if not dataset_id:
            raise DatasetError("evaluation version has no dataset_id bound — cannot execute")
        dataset = await self.repos.datasets.get_or_404(dataset_id)
        if not dataset.current_version_id:
            raise DatasetError(f"dataset '{dataset_id}' has no published version — cannot execute")
        items = await self.repos.dataset_items.list_for_version(dataset.current_version_id)
        if not items:
            raise DatasetError(f"dataset '{dataset_id}' published version has no items")
        return items

    async def _score_item(
        self, run_id: str, version: EvaluationVersionModel, item, executor: TargetExecutor
    ) -> EvaluationItemResultModel:
        try:
            exec_result = await executor.execute(version.target_config, item)
            metric_input = MetricInput(
                actual_output=exec_result.actual_output, expected_output=item.expected_output,
                latency_ms=exec_result.latency_ms, prompt_tokens=exec_result.prompt_tokens,
                completion_tokens=exec_result.completion_tokens, cost=exec_result.cost, success=exec_result.success,
            )
            metric_results = self.scorer.compute_many(version.metric_keys, metric_input, skip_errors=True)
            metric_results.update(exec_result.extra_metrics)
            scored_values = [v for v in metric_results.values() if v is not None]
            overall_score = sum(scored_values) / len(scored_values) if scored_values else None
            threshold = version.pass_threshold if version.pass_threshold is not None else 1.0
            passed = bool(exec_result.success and overall_score is not None and overall_score >= threshold)
            actual_output = exec_result.actual_output if isinstance(exec_result.actual_output, dict) else {"value": exec_result.actual_output}
            return await self.repos.evaluation_item_results.add(EvaluationItemResultModel(
                run_id=run_id, dataset_item_id=item.id, input_data=item.input_data, expected_output=item.expected_output,
                actual_output=actual_output, metric_results=metric_results, overall_score=overall_score, passed=passed,
                error_message=exec_result.error_message,
            ))
        except Exception as exc:
            return await self.repos.evaluation_item_results.add(EvaluationItemResultModel(
                run_id=run_id, dataset_item_id=item.id, input_data=item.input_data, expected_output=item.expected_output,
                actual_output={}, metric_results={}, overall_score=None, passed=False, error_message=str(exc),
            ))
