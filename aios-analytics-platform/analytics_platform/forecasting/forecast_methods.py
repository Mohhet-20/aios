"""Real, dependency-free statistical forecasting methods -- no stub
math. Each `*_forecast` function takes a chronologically-ordered
series of historical values and a horizon (number of future periods
to predict) and returns exactly `horizon` predicted values. `moving_average`
and `exponential_smoothing` intentionally produce a flat/near-flat
projection past the history they were given (that is what those
methods do); `linear_regression` is the one that extrapolates a trend.
`detect_anomalies` is a simple z-score outlier scan over the same
historical series, used to flag anomaly/risk signal in the forecast
result regardless of which method produced the projection."""
from __future__ import annotations


def moving_average_forecast(values: list[float], horizon: int, *, window: int = 3) -> list[float]:
    if not values or horizon <= 0:
        return [0.0] * max(horizon, 0)
    series = list(values)
    w = min(window, len(series))
    predictions: list[float] = []
    for _ in range(horizon):
        avg = sum(series[-w:]) / w
        predictions.append(avg)
        series.append(avg)
    return predictions


def linear_regression_forecast(values: list[float], horizon: int) -> list[float]:
    if horizon <= 0:
        return []
    n = len(values)
    if n == 0:
        return [0.0] * horizon
    if n == 1:
        return [values[0]] * horizon
    xs = list(range(n))
    mean_x = sum(xs) / n
    mean_y = sum(values) / n
    numerator = sum((x - mean_x) * (y - mean_y) for x, y in zip(xs, values))
    denominator = sum((x - mean_x) ** 2 for x in xs)
    slope = numerator / denominator if denominator else 0.0
    intercept = mean_y - slope * mean_x
    return [slope * (n + step) + intercept for step in range(horizon)]


def exponential_smoothing_forecast(values: list[float], horizon: int, *, alpha: float = 0.3) -> list[float]:
    if not values or horizon <= 0:
        return [0.0] * max(horizon, 0)
    level = values[0]
    for v in values[1:]:
        level = alpha * v + (1 - alpha) * level
    return [level] * horizon


FORECAST_METHODS = {
    "moving_average": moving_average_forecast,
    "linear_regression": linear_regression_forecast,
    "exponential_smoothing": exponential_smoothing_forecast,
}


def detect_anomalies(values: list[float], *, z_threshold: float = 2.5) -> list[dict]:
    """Flags points in the historical series more than `z_threshold`
    standard deviations from the series mean. Population std (not
    sample std) is used deliberately -- this is describing the series
    itself, not estimating a std for a larger population."""
    n = len(values)
    if n < 2:
        return []
    mean = sum(values) / n
    variance = sum((v - mean) ** 2 for v in values) / n
    std = variance ** 0.5
    if std == 0:
        return []
    anomalies = []
    for index, value in enumerate(values):
        z_score = (value - mean) / std
        if abs(z_score) >= z_threshold:
            anomalies.append({"index": index, "value": value, "z_score": round(z_score, 4)})
    return anomalies
