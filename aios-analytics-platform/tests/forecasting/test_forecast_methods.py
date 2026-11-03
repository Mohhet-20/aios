from __future__ import annotations

from analytics_platform.forecasting.forecast_methods import (
    detect_anomalies,
    exponential_smoothing_forecast,
    linear_regression_forecast,
    moving_average_forecast,
)


def test_moving_average_forecast_projects_recent_window_average():
    preds = moving_average_forecast([10.0, 20.0, 30.0], 2, window=3)
    assert len(preds) == 2
    assert preds[0] == 20.0  # avg(10,20,30)


def test_linear_regression_forecast_extrapolates_trend():
    preds = linear_regression_forecast([10.0, 20.0, 30.0, 40.0], 2)
    assert len(preds) == 2
    assert preds[0] == 50.0
    assert preds[1] == 60.0


def test_linear_regression_forecast_single_point_is_flat():
    preds = linear_regression_forecast([42.0], 3)
    assert preds == [42.0, 42.0, 42.0]


def test_exponential_smoothing_forecast_is_flat_projection():
    preds = exponential_smoothing_forecast([10.0, 20.0, 30.0], 3, alpha=0.5)
    assert len(preds) == 3
    assert preds[0] == preds[1] == preds[2]


def test_detect_anomalies_flags_outlier():
    values = [10.0, 11.0, 9.0, 10.0, 11.0, 9.0, 100.0]
    anomalies = detect_anomalies(values, z_threshold=2.0)
    assert any(a["index"] == 6 for a in anomalies)


def test_detect_anomalies_empty_for_uniform_series():
    assert detect_anomalies([5.0, 5.0, 5.0, 5.0]) == []


def test_detect_anomalies_needs_at_least_two_points():
    assert detect_anomalies([5.0]) == []
