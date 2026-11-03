"""Pure bottleneck/capacity analysis over a completed performance
run's benchmark results — no DB/service imports. Four independent
heuristics, each disclosed rather than hidden behind a single opaque
score: resource saturation (CPU/memory over threshold), error-rate
breach, and tail-latency amplification (p99 far above p50, meaning
the average looks fine but a meaningful tail of requests does not)."""
from __future__ import annotations

DEFAULT_CPU_THRESHOLD_PCT = 80.0
DEFAULT_MEMORY_THRESHOLD_PCT = 80.0
DEFAULT_ERROR_RATE_THRESHOLD_PCT = 5.0
DEFAULT_TAIL_LATENCY_RATIO_THRESHOLD = 3.0


def analyze_bottlenecks(
    metrics: dict[str, float],
    *,
    cpu_threshold_pct: float = DEFAULT_CPU_THRESHOLD_PCT,
    memory_threshold_pct: float = DEFAULT_MEMORY_THRESHOLD_PCT,
    error_rate_threshold_pct: float = DEFAULT_ERROR_RATE_THRESHOLD_PCT,
    tail_latency_ratio_threshold: float = DEFAULT_TAIL_LATENCY_RATIO_THRESHOLD,
) -> list[str]:
    """`metrics` maps `BenchmarkMetricType` values to their recorded
    value (e.g. the latest/aggregate reading per metric for the run).
    Any metric not present is simply not evaluated — this function
    never assumes a full metric set was recorded."""
    findings: list[str] = []

    cpu = metrics.get("cpu_utilization")
    if cpu is not None and cpu >= cpu_threshold_pct:
        findings.append("cpu_bound")

    memory = metrics.get("memory_utilization")
    if memory is not None and memory >= memory_threshold_pct:
        findings.append("memory_bound")

    error_rate = metrics.get("error_rate")
    if error_rate is not None and error_rate >= error_rate_threshold_pct:
        findings.append("error_rate_exceeded")

    p50 = metrics.get("latency_p50")
    p99 = metrics.get("latency_p99")
    if p50 is not None and p99 is not None and p50 > 0 and (p99 / p50) >= tail_latency_ratio_threshold:
        findings.append("tail_latency_amplification")

    return findings


def capacity_verdict(bottlenecks: list[str]) -> str:
    return "at_capacity" if bottlenecks else "healthy"
