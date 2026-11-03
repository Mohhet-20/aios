"""Pure risk-level classification — no DB/service imports. Only
`high_threshold` and `critical_threshold` are configured
(`risk_high_threshold`/`risk_critical_threshold`); the medium/low
boundary is derived as half of `high_threshold` rather than adding a
third setting nobody asked for, disclosed here rather than hidden."""
from __future__ import annotations

from quality_platform.domain.enums import RiskLevel

MEDIUM_THRESHOLD_RATIO = 0.5


def classify_risk_level(risk_score: float, *, high_threshold: float, critical_threshold: float) -> RiskLevel:
    if risk_score >= critical_threshold:
        return RiskLevel.CRITICAL
    if risk_score >= high_threshold:
        return RiskLevel.HIGH
    if risk_score >= high_threshold * MEDIUM_THRESHOLD_RATIO:
        return RiskLevel.MEDIUM
    return RiskLevel.LOW
