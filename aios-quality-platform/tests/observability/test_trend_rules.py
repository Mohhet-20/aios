from quality_platform.observability.trend_rules import compute_trend_direction


def test_too_few_points_is_stable():
    assert compute_trend_direction([]) == "stable"
    assert compute_trend_direction([50.0]) == "stable"


def test_improving_trend():
    assert compute_trend_direction([50.0, 55.0, 80.0, 90.0]) == "improving"


def test_declining_trend():
    assert compute_trend_direction([90.0, 85.0, 60.0, 50.0]) == "declining"


def test_stable_trend_within_band():
    assert compute_trend_direction([80.0, 80.5, 80.2, 80.8]) == "stable"


def test_zero_baseline_improving():
    assert compute_trend_direction([0.0, 0.0, 5.0, 5.0]) == "improving"


def test_zero_baseline_stable():
    assert compute_trend_direction([0.0, 0.0]) == "stable"
