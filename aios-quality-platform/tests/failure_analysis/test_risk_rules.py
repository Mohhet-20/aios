from quality_platform.domain.enums import RiskLevel
from quality_platform.failure_analysis.risk_rules import classify_risk_level


def test_low_risk():
    assert classify_risk_level(10.0, high_threshold=70.0, critical_threshold=90.0) == RiskLevel.LOW


def test_medium_risk():
    assert classify_risk_level(50.0, high_threshold=70.0, critical_threshold=90.0) == RiskLevel.MEDIUM


def test_high_risk():
    assert classify_risk_level(75.0, high_threshold=70.0, critical_threshold=90.0) == RiskLevel.HIGH


def test_critical_risk():
    assert classify_risk_level(95.0, high_threshold=70.0, critical_threshold=90.0) == RiskLevel.CRITICAL


def test_boundary_at_high_threshold_is_high():
    assert classify_risk_level(70.0, high_threshold=70.0, critical_threshold=90.0) == RiskLevel.HIGH
