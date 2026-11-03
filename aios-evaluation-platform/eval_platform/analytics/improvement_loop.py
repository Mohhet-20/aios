"""ImprovementLoopService: the AI Improvement Loop's evidence-gathering
half — it clusters real `EvaluationItemResultModel` failures by their
error message (or, absent an error, by which metric scored lowest),
compares recent vs. prior evaluation run history for a genuine score
regression, and turns whichever of those it actually finds into a
`RecommendationModel` with the underlying run/item ids as `evidence`.
It never invents a suggestion without a concrete evidenced trigger."""
from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timezone

from eval_platform.analytics.recommendation_service import RecommendationService
from eval_platform.models.analytics import RecommendationModel
from eval_platform.repositories.registry import RepositoryRegistry

_REGRESSION_THRESHOLD = 0.1  # absolute drop in avg overall_score that counts as a regression
_MIN_CLUSTER_SIZE = 2


def _aware(dt: datetime | None) -> datetime | None:
    if dt is not None and dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt


class ImprovementLoopService:
    def __init__(self, repos: RepositoryRegistry):
        self.repos = repos
        self.recommendations = RecommendationService(repos)

    async def cluster_run_failures(self, run_id: str) -> dict[str, list[str]]:
        """Groups failed item results by a cluster key: the error
        message when there is one, otherwise the lowest-scoring metric
        key — a simple, transparent grouping over real data, not a
        black-box ML clustering step."""
        results = await self.repos.evaluation_item_results.list_for_run(run_id)
        clusters: dict[str, list[str]] = defaultdict(list)
        for result in results:
            if result.passed:
                continue
            key = result.error_message or self._lowest_metric_key(result.metric_results) or "unclassified failure"
            clusters[key].append(result.id)
        return dict(clusters)

    def _lowest_metric_key(self, metric_results: dict) -> str | None:
        scored = {k: v for k, v in (metric_results or {}).items() if v is not None}
        if not scored:
            return None
        worst_key = min(scored, key=scored.get)
        return f"low '{worst_key}' score"

    async def detect_score_regression(self, evaluation_id: str, *, window: int = 5) -> dict | None:
        """Splits the evaluation's most recent `2 * window` scored runs
        into a recent half and a prior half and compares average
        overall_score; returns evidence only when both halves have data
        and the drop exceeds `_REGRESSION_THRESHOLD`."""
        runs = await self.repos.evaluation_runs.list_for_evaluation(evaluation_id, limit=window * 4)
        scored = [r for r in runs if r.overall_score is not None]
        scored.sort(key=lambda r: _aware(r.created_at), reverse=True)
        if len(scored) < window * 2:
            return None

        recent, prior = scored[:window], scored[window:window * 2]
        recent_avg = sum(r.overall_score for r in recent) / len(recent)
        prior_avg = sum(r.overall_score for r in prior) / len(prior)
        delta = recent_avg - prior_avg
        if delta >= -_REGRESSION_THRESHOLD:
            return None

        return {
            "evaluation_id": evaluation_id, "recent_avg_score": recent_avg, "prior_avg_score": prior_avg,
            "delta": delta, "recent_run_ids": [r.id for r in recent], "prior_run_ids": [r.id for r in prior],
        }

    async def generate_recommendations(
        self, workspace_id: str, evaluation_id: str, *, latest_run_id: str | None = None, regression_window: int = 5,
    ) -> list[RecommendationModel]:
        created: list[RecommendationModel] = []

        regression = await self.detect_score_regression(evaluation_id, window=regression_window)
        if regression is not None:
            created.append(await self.recommendations.create_recommendation(
                workspace_id, category="reliability", target_type="evaluation", target_id=evaluation_id,
                title="Quality regression detected",
                description=(
                    f"Average score dropped from {regression['prior_avg_score']:.3f} to "
                    f"{regression['recent_avg_score']:.3f} across the most recent runs."
                ),
                evidence=regression,
            ))

        if latest_run_id is not None:
            clusters = await self.cluster_run_failures(latest_run_id)
            for cluster_key, item_ids in clusters.items():
                if len(item_ids) < _MIN_CLUSTER_SIZE:
                    continue
                created.append(await self.recommendations.create_recommendation(
                    workspace_id, category="prompt_improvement", target_type="evaluation", target_id=evaluation_id,
                    title=f"Recurring failure pattern: {cluster_key}",
                    description=f"{len(item_ids)} items in run '{latest_run_id}' failed with the same pattern: {cluster_key}.",
                    evidence={"run_id": latest_run_id, "cluster_key": cluster_key, "item_result_ids": item_ids},
                ))

        return created
