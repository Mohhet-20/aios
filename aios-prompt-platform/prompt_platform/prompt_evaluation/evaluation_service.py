"""Prompt Evaluation engine: automatic (rule-based + LLM-judge) scoring,
human review capture, pairwise version comparison, and benchmark
comparison across versions — everything persisted as an EvaluationRun +
EvaluationResults.
"""
from __future__ import annotations


from ai_core.bootstrap import AICoreContext

from prompt_platform.domain.enums import EvalMetric, EvalType, RunStatus
from prompt_platform.models.evaluation import EvaluationResultModel, EvaluationRunModel
from prompt_platform.prompt_engine.render_execute import render_and_execute
from prompt_platform.prompt_evaluation.judge import judge_response
from prompt_platform.prompt_evaluation.rule_based_metrics import (
    score_cost,
    score_formatting,
    score_latency,
    score_token_usage,
)
from prompt_platform.prompt_observability.observability_service import ObservabilityService
from prompt_platform.repositories.registry import RepositoryRegistry
from prompt_platform.clock import utc_now

_JUDGE_METRICS = {EvalMetric.ACCURACY, EvalMetric.COMPLETENESS, EvalMetric.CONSISTENCY, EvalMetric.GROUNDEDNESS, EvalMetric.FAITHFULNESS, EvalMetric.SAFETY}
_RULE_METRICS = {EvalMetric.LATENCY, EvalMetric.COST, EvalMetric.TOKEN_USAGE, EvalMetric.FORMATTING}


class EvaluationService:
    def __init__(self, repos: RepositoryRegistry, ai_core: AICoreContext):
        self.repos = repos
        self.ai_core = ai_core
        self.observability = ObservabilityService(repos)

    async def run_automatic(
        self, prompt_id: str, version_id: str, *, test_inputs: list[dict], metrics: list[EvalMetric], triggered_by: str,
        reference_outputs: list[str | None] | None = None, persist_eval_score: bool = False,
    ) -> EvaluationRunModel:
        run = await self.repos.evaluation_runs.add(
            EvaluationRunModel(prompt_id=prompt_id, version_id=version_id, eval_type=EvalType.AUTOMATIC.value, status=RunStatus.RUNNING.value, triggered_by=triggered_by)
        )
        version = await self.repos.versions.get_or_404(version_id)
        references = reference_outputs or [None] * len(test_inputs)

        metric_scores: dict[str, list[float]] = {m.value: [] for m in metrics}
        for variables, reference in zip(test_inputs, references):
            prompt_text, response = await render_and_execute(
                self.ai_core, version, variables, observability=self.observability,
                prompt_id=prompt_id, version_id=version_id, source="evaluation", triggered_by=triggered_by,
            )

            for metric in metrics:
                if metric in _JUDGE_METRICS:
                    judged = await judge_response(self.ai_core, metric, prompt_text=prompt_text, response_text=response.content, reference_output=reference)
                    score, rationale, raw = judged.score, judged.rationale, judged.model_dump()
                elif metric == EvalMetric.LATENCY:
                    score, rationale, raw = score_latency(response.execution.latency_ms), None, {"latency_ms": response.execution.latency_ms}
                elif metric == EvalMetric.COST:
                    score, rationale, raw = score_cost(response.cost.total_cost_usd), None, {"cost_usd": response.cost.total_cost_usd}
                elif metric == EvalMetric.TOKEN_USAGE:
                    score, rationale, raw = score_token_usage(response.usage.total_tokens), None, {"total_tokens": response.usage.total_tokens}
                elif metric == EvalMetric.FORMATTING:
                    score, rationale, raw = score_formatting(response.content, expect_json=bool((version.parameters or {}).get("response_format"))), None, None
                else:
                    continue

                metric_scores[metric.value].append(score)
                await self.repos.evaluation_results.add(
                    EvaluationResultModel(evaluation_run_id=run.id, metric_name=metric.value, score=score, rationale=rationale, raw_output=raw)
                )

        mean_scores = {name: round(sum(scores) / len(scores), 2) for name, scores in metric_scores.items() if scores}
        overall = round(sum(mean_scores.values()) / len(mean_scores), 2) if mean_scores else 0.0

        run.status = RunStatus.COMPLETED.value
        run.completed_at = utc_now()
        run.summary = {"overall_score": overall, "metric_scores": mean_scores}
        run = await self.repos.evaluation_runs.update(run)

        if persist_eval_score:
            version.eval_score = overall
            await self.repos.versions.update(version)

        return run

    async def run_human_review(self, prompt_id: str, version_id: str, *, reviewer_id: str, score: float, rationale: str | None = None) -> EvaluationRunModel:
        run = await self.repos.evaluation_runs.add(
            EvaluationRunModel(
                prompt_id=prompt_id, version_id=version_id, eval_type=EvalType.HUMAN.value, status=RunStatus.COMPLETED.value,
                triggered_by=reviewer_id, completed_at=utc_now(), summary={"overall_score": score},
            )
        )
        await self.repos.evaluation_results.add(
            EvaluationResultModel(evaluation_run_id=run.id, metric_name=EvalMetric.USER_RATING.value, score=score, rationale=rationale)
        )
        return run

    async def run_pairwise(
        self, prompt_id: str, version_id_a: str, version_id_b: str, *, variables: dict, triggered_by: str, metric: EvalMetric = EvalMetric.ACCURACY
    ) -> EvaluationRunModel:
        run = await self.repos.evaluation_runs.add(
            EvaluationRunModel(
                prompt_id=prompt_id, version_id=version_id_a, compare_version_id=version_id_b,
                eval_type=EvalType.PAIRWISE.value, status=RunStatus.RUNNING.value, triggered_by=triggered_by,
            )
        )
        version_a = await self.repos.versions.get_or_404(version_id_a)
        version_b = await self.repos.versions.get_or_404(version_id_b)

        prompt_a, response_a = await render_and_execute(
            self.ai_core, version_a, variables, observability=self.observability,
            prompt_id=prompt_id, version_id=version_id_a, source="evaluation", triggered_by=triggered_by,
        )
        prompt_b, response_b = await render_and_execute(
            self.ai_core, version_b, variables, observability=self.observability,
            prompt_id=prompt_id, version_id=version_id_b, source="evaluation", triggered_by=triggered_by,
        )

        judged_a = await judge_response(self.ai_core, metric, prompt_text=prompt_a, response_text=response_a.content)
        judged_b = await judge_response(self.ai_core, metric, prompt_text=prompt_b, response_text=response_b.content)

        if judged_a.score > judged_b.score:
            preference = 100.0
        elif judged_b.score > judged_a.score:
            preference = 0.0
        else:
            preference = 50.0

        await self.repos.evaluation_results.add(
            EvaluationResultModel(
                evaluation_run_id=run.id, metric_name="pairwise_preference", score=preference,
                rationale=f"A={judged_a.score} ({judged_a.rationale}) | B={judged_b.score} ({judged_b.rationale})",
                raw_output={"score_a": judged_a.score, "score_b": judged_b.score},
            )
        )
        run.status = RunStatus.COMPLETED.value
        run.completed_at = utc_now()
        run.summary = {"preference_for_a": preference, "score_a": judged_a.score, "score_b": judged_b.score}
        return await self.repos.evaluation_runs.update(run)

    async def run_benchmark(
        self, prompt_id: str, version_ids: list[str], *, test_inputs: list[dict], metrics: list[EvalMetric], triggered_by: str
    ) -> dict[str, dict]:
        comparison: dict[str, dict] = {}
        for version_id in version_ids:
            run = await self.run_automatic(prompt_id, version_id, test_inputs=test_inputs, metrics=metrics, triggered_by=triggered_by)
            comparison[version_id] = run.summary
        return comparison

    async def get_results(self, evaluation_run_id: str) -> list[EvaluationResultModel]:
        return await self.repos.evaluation_results.list_for_run(evaluation_run_id)
