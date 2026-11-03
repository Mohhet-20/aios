"""Prompt Observability: records one PromptExecutionLogModel row per
render+execute call (success or failure) and rolls those rows up into
the metrics a production operator actually needs — latency percentiles,
cost, token usage, success rate, per-model breakdown, and user feedback.

`record_execution` is the single write path every execution surface
(testing, evaluation, experiments, deployment canaries) calls through —
see `prompt_engine.render_execute.render_and_execute`'s optional
`observability`/`source` params, which call back into this service so
logging happens at the one choke point every one of those call sites
already shares, rather than being bolted onto each service separately.
"""
from __future__ import annotations

import statistics
from collections import Counter

from prompt_platform.models.observability import PromptExecutionLogModel
from prompt_platform.repositories.registry import RepositoryRegistry


def _percentile(sorted_values: list[float], pct: float) -> float:
    if not sorted_values:
        return 0.0
    if len(sorted_values) == 1:
        return sorted_values[0]
    k = (len(sorted_values) - 1) * pct
    f, c = int(k), min(int(k) + 1, len(sorted_values) - 1)
    if f == c:
        return sorted_values[f]
    return sorted_values[f] + (sorted_values[c] - sorted_values[f]) * (k - f)


class ObservabilityService:
    def __init__(self, repos: RepositoryRegistry):
        self.repos = repos

    # -- recording -----------------------------------------------------------

    async def record_execution(
        self, *, prompt_id: str, version_id: str, source: str, response=None, exception: Exception | None = None,
        environment: str | None = None, triggered_by: str | None = None, correlation_id: str | None = None,
    ) -> PromptExecutionLogModel:
        if response is not None:
            log = PromptExecutionLogModel(
                prompt_id=prompt_id, version_id=version_id, environment=environment, triggered_by=triggered_by, source=source,
                model_used=response.execution.model, provider_used=response.execution.provider,
                latency_ms=response.execution.latency_ms, input_tokens=response.usage.input_tokens,
                output_tokens=response.usage.output_tokens, cost_usd=response.cost.total_cost_usd,
                success=True, retry_count=response.execution.retries, tool_calls_count=len(response.tool_calls),
                correlation_id=correlation_id,
            )
        else:
            log = PromptExecutionLogModel(
                prompt_id=prompt_id, version_id=version_id, environment=environment, triggered_by=triggered_by, source=source,
                success=False, error_message=str(exception) if exception else "unknown error", correlation_id=correlation_id,
            )
        return await self.repos.execution_logs.add(log)

    async def record_user_feedback(self, execution_log_id: str, score: float) -> PromptExecutionLogModel:
        log = await self.repos.execution_logs.get_or_404(execution_log_id)
        log.user_feedback_score = score
        return await self.repos.execution_logs.update(log)

    # -- retrieval -------------------------------------------------------------

    async def execution_history(self, prompt_id: str, *, limit: int = 100) -> list[PromptExecutionLogModel]:
        return await self.repos.execution_logs.list_for_prompt(prompt_id, limit=limit)

    async def success_rate(self, prompt_id: str) -> float:
        return await self.repos.execution_logs.success_rate(prompt_id)

    # -- analytics rollups -------------------------------------------------------

    async def analytics_summary(self, prompt_id: str, *, limit: int = 5000) -> dict:
        logs = await self.repos.execution_logs.list_for_prompt(prompt_id, limit=limit)
        total = len(logs)
        if total == 0:
            return {
                "total_executions": 0, "success_rate": 0.0, "failure_count": 0,
                "latency_ms": {"p50": 0.0, "p95": 0.0, "p99": 0.0, "avg": 0.0},
                "total_cost_usd": 0.0, "avg_cost_usd": 0.0, "total_tokens": 0,
                "model_breakdown": {}, "source_breakdown": {}, "avg_user_feedback_score": None,
                "top_failure_reasons": [],
            }

        successes = [log for log in logs if log.success]
        failures = [log for log in logs if not log.success]
        latencies = sorted(log.latency_ms for log in successes)
        feedback_scores = [log.user_feedback_score for log in logs if log.user_feedback_score is not None]

        return {
            "total_executions": total,
            "success_rate": round(len(successes) / total * 100, 2),
            "failure_count": len(failures),
            "latency_ms": {
                "p50": round(_percentile(latencies, 0.50), 2),
                "p95": round(_percentile(latencies, 0.95), 2),
                "p99": round(_percentile(latencies, 0.99), 2),
                "avg": round(statistics.mean(latencies), 2) if latencies else 0.0,
            },
            "total_cost_usd": round(sum(log.cost_usd for log in successes), 6),
            "avg_cost_usd": round(statistics.mean([log.cost_usd for log in successes]), 6) if successes else 0.0,
            "total_tokens": sum(log.input_tokens + log.output_tokens for log in successes),
            "model_breakdown": dict(Counter(log.model_used for log in successes if log.model_used)),
            "source_breakdown": dict(Counter(log.source for log in logs)),
            "avg_user_feedback_score": round(statistics.mean(feedback_scores), 2) if feedback_scores else None,
            "top_failure_reasons": Counter(log.error_message for log in failures if log.error_message).most_common(5),
        }
