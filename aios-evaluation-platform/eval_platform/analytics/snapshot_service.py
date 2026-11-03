"""AnalyticsSnapshotService: builds and persists a rollup
(quality/reliability/cost/usage/regression/trend) for a workspace over
a time window, from the platform's own already-persisted data
(EvaluationRun history, ObservabilityEvent history) — never a
fabricated number. A dashboard reads the persisted `data` dict instead
of recomputing from raw rows every time it's opened."""
from __future__ import annotations

from datetime import datetime, timezone

from eval_platform.core.exceptions import ValidationError
from eval_platform.domain.enums import AnalyticsSnapshotType
from eval_platform.models.analytics import AnalyticsSnapshotModel
from eval_platform.repositories.registry import RepositoryRegistry


def _aware(dt: datetime | None) -> datetime | None:
    if dt is not None and dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt


def _in_window(created_at, period_start: datetime, period_end: datetime) -> bool:
    created_at = _aware(created_at)
    return created_at is not None and period_start <= created_at <= period_end


class AnalyticsSnapshotService:
    def __init__(self, repos: RepositoryRegistry):
        self.repos = repos

    async def list_snapshots(self, workspace_id: str, *, snapshot_type: str | None = None) -> list[AnalyticsSnapshotModel]:
        return await self.repos.analytics_snapshots.list_for_workspace(workspace_id, snapshot_type=snapshot_type)

    async def build_quality_snapshot(self, workspace_id: str, *, period_start: datetime, period_end: datetime) -> AnalyticsSnapshotModel:
        runs = await self._runs_in_window(workspace_id, period_start, period_end)
        scored = [r for r in runs if r.overall_score is not None]
        data = {
            "run_count": len(runs), "scored_run_count": len(scored),
            "avg_overall_score": (sum(r.overall_score for r in scored) / len(scored)) if scored else None,
            "pass_rate": (sum(1 for r in runs if r.item_count and r.passed_count == r.item_count) / len(runs)) if runs else None,
        }
        return await self._persist(workspace_id, AnalyticsSnapshotType.QUALITY.value, period_start, period_end, data)

    async def build_reliability_snapshot(self, workspace_id: str, *, period_start: datetime, period_end: datetime) -> AnalyticsSnapshotModel:
        events = await self._events_in_window(workspace_id, period_start, period_end)
        failed = [e for e in events if e.status == "failed"]
        data = {
            "event_count": len(events), "failure_count": len(failed),
            "failure_rate": (len(failed) / len(events)) if events else None,
            "total_retries": sum(e.retry_count for e in events),
        }
        return await self._persist(workspace_id, AnalyticsSnapshotType.RELIABILITY.value, period_start, period_end, data)

    async def build_cost_snapshot(self, workspace_id: str, *, period_start: datetime, period_end: datetime) -> AnalyticsSnapshotModel:
        events = await self._events_in_window(workspace_id, period_start, period_end)
        costs = [e.cost for e in events if e.cost is not None]
        data = {"total_cost": sum(costs) if costs else None, "cost_sample_count": len(costs)}
        return await self._persist(workspace_id, AnalyticsSnapshotType.COST.value, period_start, period_end, data)

    async def build_usage_snapshot(self, workspace_id: str, *, period_start: datetime, period_end: datetime) -> AnalyticsSnapshotModel:
        events = await self._events_in_window(workspace_id, period_start, period_end)
        by_type: dict[str, int] = {}
        for event in events:
            by_type[event.event_type] = by_type.get(event.event_type, 0) + 1
        input_tokens = sum(e.token_usage.get("input_tokens", 0) for e in events if e.token_usage)
        output_tokens = sum(e.token_usage.get("output_tokens", 0) for e in events if e.token_usage)
        data = {"event_count_by_type": by_type, "total_events": len(events), "input_tokens": input_tokens, "output_tokens": output_tokens}
        return await self._persist(workspace_id, AnalyticsSnapshotType.USAGE.value, period_start, period_end, data)

    async def build_regression_snapshot(
        self, workspace_id: str, evaluation_id: str, *, period_start: datetime, period_end: datetime, previous_period_start: datetime,
    ) -> AnalyticsSnapshotModel:
        if previous_period_start >= period_start:
            raise ValidationError("previous_period_start must be before period_start")
        current_runs = [r for r in await self._runs_in_window(workspace_id, period_start, period_end) if r.evaluation_id == evaluation_id and r.overall_score is not None]
        previous_runs = [r for r in await self._runs_in_window(workspace_id, previous_period_start, period_start) if r.evaluation_id == evaluation_id and r.overall_score is not None]

        current_avg = (sum(r.overall_score for r in current_runs) / len(current_runs)) if current_runs else None
        previous_avg = (sum(r.overall_score for r in previous_runs) / len(previous_runs)) if previous_runs else None
        delta = (current_avg - previous_avg) if (current_avg is not None and previous_avg is not None) else None
        data = {
            "evaluation_id": evaluation_id, "current_avg_score": current_avg, "previous_avg_score": previous_avg,
            "delta": delta, "regressed": bool(delta is not None and delta < 0),
            "current_run_count": len(current_runs), "previous_run_count": len(previous_runs),
        }
        return await self._persist(workspace_id, AnalyticsSnapshotType.REGRESSION.value, period_start, period_end, data)

    async def build_trend_snapshot(self, workspace_id: str, evaluation_id: str, *, period_start: datetime, period_end: datetime) -> AnalyticsSnapshotModel:
        runs = [r for r in await self._runs_in_window(workspace_id, period_start, period_end) if r.evaluation_id == evaluation_id and r.overall_score is not None]
        by_day: dict[str, list[float]] = {}
        for run in sorted(runs, key=lambda r: _aware(r.created_at)):
            day = _aware(run.created_at).date().isoformat()
            by_day.setdefault(day, []).append(run.overall_score)
        points = [{"date": day, "avg_score": sum(scores) / len(scores), "run_count": len(scores)} for day, scores in sorted(by_day.items())]
        data = {"evaluation_id": evaluation_id, "points": points}
        return await self._persist(workspace_id, AnalyticsSnapshotType.TREND.value, period_start, period_end, data)

    async def _runs_in_window(self, workspace_id: str, period_start: datetime, period_end: datetime):
        runs = await self.repos.evaluation_runs.list_for_workspace(workspace_id, limit=5000)
        return [r for r in runs if _in_window(r.created_at, period_start, period_end)]

    async def _events_in_window(self, workspace_id: str, period_start: datetime, period_end: datetime):
        events = await self.repos.observability_events.list_for_workspace(workspace_id, limit=5000)
        return [e for e in events if _in_window(e.created_at, period_start, period_end)]

    async def _persist(self, workspace_id: str, snapshot_type: str, period_start: datetime, period_end: datetime, data: dict) -> AnalyticsSnapshotModel:
        return await self.repos.analytics_snapshots.add(AnalyticsSnapshotModel(
            workspace_id=workspace_id, snapshot_type=snapshot_type, period_start=period_start, period_end=period_end, data=data,
        ))
