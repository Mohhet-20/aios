from types import SimpleNamespace

from release_platform.analytics.aggregation_rules import (
    average_deployment_duration,
    deployment_success_rate,
    failed_release_count,
    rollback_frequency,
)


def _metric(metric_type, value=0.0):
    return SimpleNamespace(metric_type=metric_type, value=value)


def test_deployment_success_rate_none_when_empty():
    assert deployment_success_rate([]) is None


def test_deployment_success_rate_computes_fraction():
    metrics = [_metric("deployment_succeeded")] * 3 + [_metric("deployment_failed")]
    assert deployment_success_rate(metrics) == 0.75


def test_rollback_frequency_none_when_no_outcomes():
    assert rollback_frequency([]) is None


def test_rollback_frequency_computes_ratio():
    metrics = [_metric("deployment_succeeded")] * 4 + [_metric("rollback_triggered")]
    assert rollback_frequency(metrics) == 0.25


def test_average_deployment_duration_none_when_empty():
    assert average_deployment_duration([]) is None


def test_average_deployment_duration_computes_mean():
    metrics = [_metric("deployment_duration_seconds", 10.0), _metric("deployment_duration_seconds", 20.0)]
    assert average_deployment_duration(metrics) == 15.0


def test_failed_release_count():
    metrics = [_metric("release_failed")] * 2 + [_metric("deployment_succeeded")]
    assert failed_release_count(metrics) == 2
