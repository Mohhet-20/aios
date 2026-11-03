from quality_platform.domain.enums import RegressionSeverity
from quality_platform.ai_quality.regression_rules import classify_regression, compute_delta_pct


def test_compute_delta_pct_improvement():
    assert compute_delta_pct(80.0, 90.0) == 12.5


def test_compute_delta_pct_zero_baseline_zero_current():
    assert compute_delta_pct(0.0, 0.0) == 0.0


def test_compute_delta_pct_zero_baseline_positive_current():
    assert compute_delta_pct(0.0, 10.0) == 100.0


def test_classify_regression_no_drift_on_improvement():
    delta, severity = classify_regression(80.0, 90.0, threshold_pct=5.0)
    assert delta > 0
    assert severity == RegressionSeverity.NONE


def test_classify_regression_minor():
    delta, severity = classify_regression(100.0, 94.0, threshold_pct=5.0)  # -6%
    assert severity == RegressionSeverity.MINOR


def test_classify_regression_major():
    delta, severity = classify_regression(100.0, 88.0, threshold_pct=5.0)  # -12%
    assert severity == RegressionSeverity.MAJOR


def test_classify_regression_critical():
    delta, severity = classify_regression(100.0, 80.0, threshold_pct=5.0)  # -20%
    assert severity == RegressionSeverity.CRITICAL


def test_classify_regression_below_threshold_is_none():
    delta, severity = classify_regression(100.0, 98.0, threshold_pct=5.0)  # -2%
    assert severity == RegressionSeverity.NONE
