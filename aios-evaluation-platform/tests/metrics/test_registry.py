import pytest

from eval_platform.core.exceptions import UnknownMetricError
from eval_platform.domain.enums import MetricCategory
from eval_platform.metrics.registry import METRIC_SPECS, get_metric_spec


def test_registry_covers_every_metric_category_exactly_once():
    keys = [spec.category for spec in METRIC_SPECS]
    assert len(keys) == len(MetricCategory)
    assert set(keys) == {c.value for c in MetricCategory}
    assert len(keys) == len(set(keys))


def test_every_spec_key_is_unique():
    keys = [spec.key for spec in METRIC_SPECS]
    assert len(keys) == len(set(keys))


def test_get_metric_spec_returns_correct_spec():
    spec = get_metric_spec("groundedness")
    assert spec.name == "Groundedness"
    assert spec.higher_is_better is True


def test_get_metric_spec_unknown_raises():
    with pytest.raises(UnknownMetricError):
        get_metric_spec("not_a_real_metric")
