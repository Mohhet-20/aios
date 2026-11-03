from quality_platform.performance.bottleneck_rules import analyze_bottlenecks, capacity_verdict


def test_no_bottlenecks_when_metrics_healthy():
    findings = analyze_bottlenecks({"cpu_utilization": 40.0, "memory_utilization": 50.0, "error_rate": 0.5})
    assert findings == []
    assert capacity_verdict(findings) == "healthy"


def test_cpu_bound_detected():
    findings = analyze_bottlenecks({"cpu_utilization": 92.0})
    assert "cpu_bound" in findings
    assert capacity_verdict(findings) == "at_capacity"


def test_memory_bound_detected():
    findings = analyze_bottlenecks({"memory_utilization": 85.0})
    assert "memory_bound" in findings


def test_error_rate_exceeded_detected():
    findings = analyze_bottlenecks({"error_rate": 10.0})
    assert "error_rate_exceeded" in findings


def test_tail_latency_amplification_detected():
    findings = analyze_bottlenecks({"latency_p50": 50.0, "latency_p99": 200.0})
    assert "tail_latency_amplification" in findings


def test_tail_latency_not_flagged_when_close_to_p50():
    findings = analyze_bottlenecks({"latency_p50": 50.0, "latency_p99": 80.0})
    assert "tail_latency_amplification" not in findings


def test_missing_metrics_are_skipped_not_flagged():
    assert analyze_bottlenecks({}) == []
