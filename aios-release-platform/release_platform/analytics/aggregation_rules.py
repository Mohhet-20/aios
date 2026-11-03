"""Pure aggregation helpers over already-fetched metric rows. No DB or
service imports — the service layer fetches rows and hands them here,
mirroring `docs_platform.analytics.aggregation_rules`'s split between
fetching and computing."""
from __future__ import annotations

_SUCCESS = "deployment_succeeded"
_FAILURE = "deployment_failed"
_DURATION = "deployment_duration_seconds"
_ROLLBACK = "rollback_triggered"
_RELEASE_FAILED = "release_failed"


def deployment_success_rate(metrics: list) -> float | None:
    outcomes = [m for m in metrics if m.metric_type in (_SUCCESS, _FAILURE)]
    if not outcomes:
        return None
    successes = sum(1 for m in outcomes if m.metric_type == _SUCCESS)
    return successes / len(outcomes)


def rollback_frequency(metrics: list) -> float | None:
    outcomes = [m for m in metrics if m.metric_type in (_SUCCESS, _FAILURE)]
    if not outcomes:
        return None
    rollbacks = sum(1 for m in metrics if m.metric_type == _ROLLBACK)
    return rollbacks / len(outcomes)


def average_deployment_duration(metrics: list) -> float | None:
    durations = [m.value for m in metrics if m.metric_type == _DURATION]
    if not durations:
        return None
    return sum(durations) / len(durations)


def failed_release_count(metrics: list) -> int:
    return sum(1 for m in metrics if m.metric_type == _RELEASE_FAILED)
