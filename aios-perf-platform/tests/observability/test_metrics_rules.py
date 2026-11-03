from __future__ import annotations

import pytest

from perf_platform.observability.metrics_rules import improvement_pct, mean, percentile, throughput_per_second


def test_percentile_p50_p99():
    values = list(range(1, 101))  # 1..100
    assert percentile(values, 50) == 50
    assert percentile(values, 99) == 99
    assert percentile(values, 100) == 100
    assert percentile(values, 0) == 1


def test_percentile_empty_list():
    assert percentile([], 95) == 0.0


def test_percentile_invalid_pct_raises():
    with pytest.raises(ValueError):
        percentile([1, 2, 3], 150)


def test_mean():
    assert mean([1, 2, 3]) == 2.0
    assert mean([]) == 0.0


def test_throughput_per_second():
    assert throughput_per_second(request_count=600, window_seconds=60) == 10.0
    assert throughput_per_second(request_count=100, window_seconds=0) == 0.0


def test_improvement_pct_speedup_and_regression():
    assert improvement_pct(baseline_ms=100, optimized_ms=50) == 50.0
    assert improvement_pct(baseline_ms=100, optimized_ms=150) == -50.0
    assert improvement_pct(baseline_ms=0, optimized_ms=50) == 0.0
