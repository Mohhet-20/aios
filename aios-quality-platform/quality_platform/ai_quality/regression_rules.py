"""Pure regression-classification logic — no DB/service imports. A
regression scan compares a fresh evaluation score against its stored
baseline; `delta_pct` is signed (positive = improvement, negative =
drop), and severity is only ever assigned on a drop, classified in
multiples of the configured threshold (`ai_quality_regression_threshold_pct`):
[threshold, 2x) -> minor, [2x, 3x) -> major, [3x, inf) -> critical."""
from __future__ import annotations

from quality_platform.domain.enums import RegressionSeverity


def compute_delta_pct(baseline_score: float, current_score: float) -> float:
    """Signed percent change from baseline to current. Baseline of
    zero is a degenerate case (nothing to divide by): treated as no
    drift if current is also zero, otherwise as a full-magnitude swing
    in the direction current moved, mirroring the zero-division
    convention disclosed elsewhere in this platform family
    (analytics_platform's ForecastAccuracyService.compute_error_pct)."""
    if baseline_score == 0:
        if current_score == 0:
            return 0.0
        return 100.0 if current_score > 0 else -100.0
    return (current_score - baseline_score) / baseline_score * 100.0


def classify_severity(delta_pct: float, *, threshold_pct: float) -> RegressionSeverity:
    if delta_pct >= 0:
        return RegressionSeverity.NONE
    drop = abs(delta_pct)
    if drop >= threshold_pct * 3:
        return RegressionSeverity.CRITICAL
    if drop >= threshold_pct * 2:
        return RegressionSeverity.MAJOR
    if drop >= threshold_pct:
        return RegressionSeverity.MINOR
    return RegressionSeverity.NONE


def classify_regression(baseline_score: float, current_score: float, *, threshold_pct: float) -> tuple[float, RegressionSeverity]:
    delta_pct = compute_delta_pct(baseline_score, current_score)
    return delta_pct, classify_severity(delta_pct, threshold_pct=threshold_pct)
