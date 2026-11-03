"""BenchmarkRunService: executes a `BenchmarkRunModel`'s named
candidates (model variants, prompt versions for A/B/multivariate
testing, or agent/workflow variants) against the same dataset and
metric set, producing one `BenchmarkCandidateResultModel` per candidate
— what a Model or Prompt Comparison dashboard renders as columns.
Reuses the exact same `TargetExecutor` seam and dataset-loading logic
as `EvaluationRunService`, since a benchmark is a multi-candidate
generalization of a single evaluation run."""
from __future__ import annotations

from eval_platform.core.exceptions import BenchmarkError, DatasetError
from eval_platform.domain.entities import BenchmarkRun
from eval_platform.domain.enums import RunStatus
from eval_platform.execution.executor import TargetExecutor
from eval_platform.metrics.inputs import MetricInput
from eval_platform.metrics.scorer import MetricScorer
from eval_platform.models.benchmark import BenchmarkCandidateResultModel, BenchmarkModel, BenchmarkRunModel
from eval_platform.repositories.registry import RepositoryRegistry


def _run_to_domain(model: BenchmarkRunModel) -> BenchmarkRun:
    return BenchmarkRun(
        id=model.id, benchmark_id=model.benchmark_id, workspace_id=model.workspace_id, status=RunStatus(model.status),
        attempt_number=1, max_retries=0, candidates=list(model.candidates or []), error_message=model.error_message,
        started_at=model.started_at, completed_at=model.completed_at, duration_ms=model.duration_ms,
    )


def _apply_run_to_model(entity: BenchmarkRun, model: BenchmarkRunModel) -> None:
    model.status = entity.status.value
    model.error_message = entity.error_message
    model.started_at = entity.started_at
    model.completed_at = entity.completed_at
    model.duration_ms = entity.duration_ms


class BenchmarkRunService:
    def __init__(self, repos: RepositoryRegistry):
        self.repos = repos
        self.scorer = MetricScorer(repos)

    async def start_run(self, benchmark_id: str, candidates: list[dict], *, triggered_by: str | None = None) -> BenchmarkRunModel:
        benchmark = await self.repos.benchmarks.get_or_404(benchmark_id)
        if len(candidates) < 1:
            raise BenchmarkError("a benchmark run needs at least one candidate")
        labels = [c.get("label") for c in candidates]
        if any(not label for label in labels):
            raise BenchmarkError("every candidate must have a non-empty 'label'")
        if len(set(labels)) != len(labels):
            raise BenchmarkError(f"candidate labels must be unique, got: {labels}")

        return await self.repos.benchmark_runs.add(BenchmarkRunModel(
            benchmark_id=benchmark_id, workspace_id=benchmark.workspace_id, candidates=candidates, triggered_by=triggered_by,
        ))

    async def get_run(self, run_id: str) -> BenchmarkRunModel:
        return await self.repos.benchmark_runs.get_or_404(run_id)

    async def list_runs(self, benchmark_id: str) -> list[BenchmarkRunModel]:
        return await self.repos.benchmark_runs.list_for_benchmark(benchmark_id)

    async def list_candidate_results(self, run_id: str) -> list[BenchmarkCandidateResultModel]:
        return await self.repos.benchmark_candidate_results.list_for_run(run_id)

    async def leaderboard(self, run_id: str) -> list[BenchmarkCandidateResultModel]:
        """Candidate results ordered best-first by `aggregate_score`.
        Assumes the benchmark's configured metrics are higher-is-better
        (the common case: accuracy/quality-style metrics); a caller
        comparing on a lower-is-better metric set (pure latency/cost)
        should sort the raw results itself."""
        results = await self.list_candidate_results(run_id)
        return sorted(results, key=lambda r: (r.aggregate_score is None, -(r.aggregate_score or 0.0)))

    async def execute_run(self, run_id: str, executor: TargetExecutor) -> BenchmarkRunModel:
        model = await self.repos.benchmark_runs.get_or_404(run_id)
        entity = _run_to_domain(model)
        entity.start()
        _apply_run_to_model(entity, model)
        model = await self.repos.benchmark_runs.update(model)

        benchmark = await self.repos.benchmarks.get_or_404(model.benchmark_id)
        try:
            items = await self._load_items(benchmark)
            for candidate in model.candidates:
                await self._score_candidate(model.id, benchmark, candidate, items, executor)

            entity = _run_to_domain(model)
            entity.succeed()
            _apply_run_to_model(entity, model)
            return await self.repos.benchmark_runs.update(model)
        except Exception as exc:
            entity = _run_to_domain(model)
            entity.fail(str(exc))
            _apply_run_to_model(entity, model)
            await self.repos.benchmark_runs.update(model)
            raise

    async def _load_items(self, benchmark: BenchmarkModel):
        if not benchmark.dataset_id:
            raise DatasetError(f"benchmark '{benchmark.id}' has no dataset_id bound — cannot execute")
        dataset = await self.repos.datasets.get_or_404(benchmark.dataset_id)
        if not dataset.current_version_id:
            raise DatasetError(f"dataset '{benchmark.dataset_id}' has no published version — cannot execute")
        items = await self.repos.dataset_items.list_for_version(dataset.current_version_id)
        if not items:
            raise DatasetError(f"dataset '{benchmark.dataset_id}' published version has no items")
        return items

    async def _score_candidate(self, run_id: str, benchmark: BenchmarkModel, candidate: dict, items: list, executor: TargetExecutor) -> BenchmarkCandidateResultModel:
        metric_totals: dict[str, list[float]] = {}
        latencies: list[float] = []
        total_cost = 0.0
        has_cost = False
        prompt_tokens_total = 0
        completion_tokens_total = 0
        failure_count = 0

        for item in items:
            try:
                exec_result = await executor.execute(candidate, item)
            except Exception as exc:
                failure_count += 1
                metric_totals.setdefault("__error__", []).append(1.0)
                _ = exc
                continue

            if not exec_result.success:
                failure_count += 1

            metric_input = MetricInput(
                actual_output=exec_result.actual_output, expected_output=item.expected_output,
                latency_ms=exec_result.latency_ms, prompt_tokens=exec_result.prompt_tokens,
                completion_tokens=exec_result.completion_tokens, cost=exec_result.cost, success=exec_result.success,
            )
            metric_results = self.scorer.compute_many(benchmark.metric_keys, metric_input, skip_errors=True)
            metric_results.update(exec_result.extra_metrics)
            for key, value in metric_results.items():
                if value is not None:
                    metric_totals.setdefault(key, []).append(value)

            if exec_result.latency_ms is not None:
                latencies.append(exec_result.latency_ms)
            if exec_result.cost is not None:
                total_cost += exec_result.cost
                has_cost = True
            if exec_result.prompt_tokens:
                prompt_tokens_total += exec_result.prompt_tokens
            if exec_result.completion_tokens:
                completion_tokens_total += exec_result.completion_tokens

        metric_totals.pop("__error__", None)
        metric_averages = {key: sum(values) / len(values) for key, values in metric_totals.items()}
        aggregate_score = (sum(metric_averages.values()) / len(metric_averages)) if metric_averages else None

        return await self.repos.benchmark_candidate_results.add(BenchmarkCandidateResultModel(
            benchmark_run_id=run_id, candidate_label=candidate["label"], metric_results=metric_averages,
            aggregate_score=aggregate_score, avg_latency_ms=(sum(latencies) / len(latencies)) if latencies else None,
            total_cost=total_cost if has_cost else None,
            token_usage={"prompt_tokens": prompt_tokens_total, "completion_tokens": completion_tokens_total},
            item_count=len(items), failure_count=failure_count,
        ))
