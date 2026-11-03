"""Prompt Experiments platform: A/B and multi-variant testing across
prompt versions, models, and parameters, with statistically-grounded
winner selection and seed-based reproducibility.

Each variant maps to a prompt version plus optional model/provider/
temperature/parameter overrides, so an experiment can compare "same
prompt, different model" just as easily as "different prompt, same
model." Execution reuses the Evaluation engine's judge/rule-based
scoring (prompt_evaluation.judge / rule_based_metrics) so a variant's
"score" for a given metric means the same thing here as it does in a
standalone evaluation run.
"""
from __future__ import annotations

import random
from dataclasses import dataclass


from ai_core.bootstrap import AICoreContext

from prompt_platform.core.exceptions import InvalidTransitionError, NotFoundError, ValidationError
from prompt_platform.domain.enums import EvalMetric, ExperimentStatus
from prompt_platform.models.experiment import ExperimentModel, ExperimentResultModel, ExperimentVariantModel
from prompt_platform.prompt_engine.render_execute import render_and_execute
from prompt_platform.prompt_evaluation.judge import _METRIC_INSTRUCTIONS, judge_response
from prompt_platform.prompt_evaluation.rule_based_metrics import (
    score_cost,
    score_formatting,
    score_latency,
    score_token_usage,
)
from prompt_platform.prompt_experiments.statistics import select_winner, summarize
from prompt_platform.prompt_observability.observability_service import ObservabilityService
from prompt_platform.repositories.registry import RepositoryRegistry
from prompt_platform.clock import utc_now

_RULE_METRICS = {EvalMetric.LATENCY, EvalMetric.COST, EvalMetric.TOKEN_USAGE, EvalMetric.FORMATTING}


@dataclass
class _EffectiveVersion:
    """A prompt version's templates with a variant's overrides folded
    into `parameters` — built in memory, never persisted, so comparing
    variants never mutates the underlying PromptVersionModel rows."""
    system_template: str | None
    developer_template: str | None
    user_template: str
    parameters: dict


class ExperimentService:
    def __init__(self, repos: RepositoryRegistry, ai_core: AICoreContext):
        self.repos = repos
        self.ai_core = ai_core
        self.observability = ObservabilityService(repos)

    # -- setup -------------------------------------------------------------

    async def create_experiment(
        self, workspace_id: str, prompt_id: str, *, name: str, actor_id: str,
        description: str | None = None, hypothesis: str | None = None,
        sample_size_per_variant: int = 10, random_seed: int = 42,
    ) -> ExperimentModel:
        experiment = ExperimentModel(
            workspace_id=workspace_id, prompt_id=prompt_id, name=name, description=description,
            hypothesis=hypothesis, status=ExperimentStatus.DRAFT.value,
            sample_size_per_variant=sample_size_per_variant, random_seed=random_seed, created_by=actor_id,
        )
        return await self.repos.experiments.add(experiment)

    async def add_variant(
        self, experiment_id: str, *, name: str, prompt_version_id: str | None = None,
        model_override: str | None = None, provider_override: str | None = None,
        temperature_override: float | None = None, parameter_overrides: dict | None = None,
        traffic_percent: float = 50.0,
    ) -> ExperimentVariantModel:
        experiment = await self.repos.experiments.get_or_404(experiment_id)
        if experiment.status != ExperimentStatus.DRAFT.value:
            raise InvalidTransitionError(f"Cannot add variants to an experiment in status '{experiment.status}'")
        variant = ExperimentVariantModel(
            experiment_id=experiment_id, name=name, prompt_version_id=prompt_version_id,
            model_override=model_override, provider_override=provider_override,
            temperature_override=temperature_override, parameter_overrides=parameter_overrides or {},
            traffic_percent=traffic_percent,
        )
        return await self.repos.experiment_variants.add(variant)

    async def start_experiment(self, experiment_id: str) -> ExperimentModel:
        experiment = await self.repos.experiments.get_or_404(experiment_id)
        if experiment.status != ExperimentStatus.DRAFT.value:
            raise InvalidTransitionError(f"Cannot start an experiment in status '{experiment.status}'")
        variants = await self.repos.experiment_variants.list_for_experiment(experiment_id)
        if len(variants) < 2:
            raise ValidationError("An experiment needs at least 2 variants before it can be started")
        experiment.status = ExperimentStatus.RUNNING.value
        experiment.started_at = utc_now()
        return await self.repos.experiments.update(experiment)

    # -- execution -----------------------------------------------------------

    async def _resolve_effective_version(self, variant: ExperimentVariantModel) -> _EffectiveVersion:
        if not variant.prompt_version_id:
            raise ValidationError(f"Variant '{variant.name}' has no prompt_version_id to execute")
        base = await self.repos.versions.get_or_404(variant.prompt_version_id)
        params = dict(base.parameters or {})
        if variant.model_override:
            params["model"] = variant.model_override
        if variant.provider_override:
            params["provider"] = variant.provider_override
        if variant.temperature_override is not None:
            params["temperature"] = variant.temperature_override
        params.update(variant.parameter_overrides or {})
        return _EffectiveVersion(base.system_template, base.developer_template, base.user_template, params)

    def _sample_inputs(self, experiment: ExperimentModel, test_inputs: list[dict], *, salt: str) -> list[dict]:
        """Reproducible sampling: the same `random_seed` + variant salt
        always yields the same sequence of test inputs, so re-running an
        experiment (or auditing one later) reproduces identical inputs
        per variant. Samples with replacement so `sample_size_per_variant`
        can exceed the number of distinct test inputs supplied."""
        rng = random.Random(f"{experiment.random_seed}:{salt}")
        if not test_inputs:
            return []
        return [rng.choice(test_inputs) for _ in range(experiment.sample_size_per_variant)]

    async def _score_one(
        self, effective_version: _EffectiveVersion, variables: dict, metric: EvalMetric, *, prompt_id: str, version_id: str, triggered_by: str,
    ) -> float:
        prompt_text, response = await render_and_execute(
            self.ai_core, effective_version, variables, observability=self.observability,
            prompt_id=prompt_id, version_id=version_id, source="experiment", triggered_by=triggered_by,
        )
        if metric in _METRIC_INSTRUCTIONS:
            judged = await judge_response(self.ai_core, metric, prompt_text=prompt_text, response_text=response.content)
            return judged.score
        if metric == EvalMetric.LATENCY:
            return score_latency(response.execution.latency_ms)
        if metric == EvalMetric.COST:
            return score_cost(response.cost.total_cost_usd)
        if metric == EvalMetric.TOKEN_USAGE:
            return score_token_usage(response.usage.total_tokens)
        if metric == EvalMetric.FORMATTING:
            return score_formatting(response.content)
        raise ValidationError(f"Unsupported experiment metric: {metric}")

    async def run(
        self, experiment_id: str, *, test_inputs: list[dict], metric: EvalMetric = EvalMetric.ACCURACY, triggered_by: str,
    ) -> ExperimentModel:
        experiment = await self.repos.experiments.get_or_404(experiment_id)
        if experiment.status != ExperimentStatus.RUNNING.value:
            raise InvalidTransitionError(f"Cannot run an experiment in status '{experiment.status}' — call start_experiment() first")
        variants = await self.repos.experiment_variants.list_for_experiment(experiment_id)
        if not test_inputs:
            raise ValidationError("At least one test input is required to run an experiment")

        variant_scores: dict[str, list[float]] = {}
        for variant in variants:
            effective_version = await self._resolve_effective_version(variant)
            sampled = self._sample_inputs(experiment, test_inputs, salt=variant.id)
            scores = [
                await self._score_one(
                    effective_version, variables, metric,
                    prompt_id=experiment.prompt_id, version_id=variant.prompt_version_id, triggered_by=triggered_by,
                )
                for variables in sampled
            ]
            variant_scores[variant.id] = scores

            summary = summarize(scores)
            await self.repos.experiment_results.add(
                ExperimentResultModel(
                    experiment_id=experiment_id, variant_id=variant.id, metric_name=metric.value,
                    mean_score=summary.mean, stddev=summary.stddev, sample_size=summary.n, raw_scores=scores,
                )
            )

        winner = select_winner(variant_scores)
        experiment.status = ExperimentStatus.COMPLETED.value
        experiment.completed_at = utc_now()
        experiment.winner_variant_id = winner.leader_variant_id
        return await self.repos.experiments.update(experiment)

    # -- analysis ------------------------------------------------------------

    async def statistical_summary(self, experiment_id: str, *, metric: EvalMetric = EvalMetric.ACCURACY) -> dict:
        results = await self.repos.experiment_results.list_for_experiment(experiment_id)
        relevant = [r for r in results if r.metric_name == metric.value]
        if not relevant:
            raise NotFoundError(f"No results recorded for metric '{metric.value}' on experiment '{experiment_id}'")
        variant_scores = {r.variant_id: r.raw_scores for r in relevant}
        winner = select_winner(variant_scores)
        return {
            "metric": metric.value,
            "leader_variant_id": winner.leader_variant_id,
            "significant_winner": winner.significant_winner,
            "means": winner.means,
            "comparisons": winner.comparisons,
        }

    async def get_results(self, experiment_id: str) -> list[ExperimentResultModel]:
        return await self.repos.experiment_results.list_for_experiment(experiment_id)

    async def list_variants(self, experiment_id: str) -> list[ExperimentVariantModel]:
        return await self.repos.experiment_variants.list_for_experiment(experiment_id)

    async def list_experiments(self, workspace_id: str) -> list[ExperimentModel]:
        return await self.repos.experiments.list_for_workspace(workspace_id)

    async def archive(self, experiment_id: str) -> ExperimentModel:
        experiment = await self.repos.experiments.get_or_404(experiment_id)
        experiment.status = ExperimentStatus.ARCHIVED.value
        return await self.repos.experiments.update(experiment)
