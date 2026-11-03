import pytest

from eval_platform.core.exceptions import UnknownEvaluationTypeError
from eval_platform.domain.enums import EvaluationCategory
from eval_platform.evaluation_core.registry import EVALUATION_TYPE_SPECS, get_evaluation_type_spec


def test_registry_covers_every_evaluation_category_exactly_once():
    keys = [spec.key for spec in EVALUATION_TYPE_SPECS]
    assert len(keys) == len(EvaluationCategory)
    assert set(keys) == {c.value for c in EvaluationCategory}
    assert len(keys) == len(set(keys))


def test_get_evaluation_type_spec_returns_correct_spec():
    spec = get_evaluation_type_spec("groundedness")
    assert spec.name == "Groundedness Evaluation"
    assert "hallucination_rate" in spec.recommended_metric_keys


def test_get_evaluation_type_spec_unknown_raises():
    with pytest.raises(UnknownEvaluationTypeError):
        get_evaluation_type_spec("not_a_real_category")
