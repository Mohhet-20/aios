from quality_platform.domain.enums import SloStatus
from quality_platform.reliability.slo_rules import classify_slo_status, compute_error_budget_remaining_pct


def test_meeting_when_comfortably_above_target():
    assert classify_slo_status(99.99, 99.0) == SloStatus.MEETING


def test_at_risk_when_close_to_target():
    assert classify_slo_status(99.95, 99.9, at_risk_margin_pct=0.1) == SloStatus.AT_RISK


def test_breached_when_below_target():
    assert classify_slo_status(99.5, 99.9) == SloStatus.BREACHED


def test_error_budget_full_at_target():
    assert compute_error_budget_remaining_pct(99.9, 99.9) == 100.0


def test_error_budget_half_consumed():
    # target 99.9 -> budget 0.1pp; current 99.85 consumed half of it
    assert round(compute_error_budget_remaining_pct(99.85, 99.9), 1) == 50.0


def test_error_budget_negative_when_over():
    assert compute_error_budget_remaining_pct(99.7, 99.9) < 0


def test_error_budget_zero_width_target():
    assert compute_error_budget_remaining_pct(100.0, 100.0) == 100.0
    assert compute_error_budget_remaining_pct(99.9, 100.0) == 0.0
