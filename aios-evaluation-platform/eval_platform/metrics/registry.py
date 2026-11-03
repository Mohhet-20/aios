"""The in-code catalog of all 20 built-in quality metrics — the actual
computation functions live in `functions.py`; `MetricDefinitionModel`
(seeded from `MetricSpec.as_definition_kwargs()` by `scorer.py`) is what
a Quality Scorecard UI queries without importing Python, mirroring
`evaluation_core/registry.py`'s `EvaluationTypeSpec` pattern."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

from eval_platform.domain.enums import MetricCategory, MetricValueType
from eval_platform.metrics import functions as fn
from eval_platform.metrics.inputs import MetricInput


@dataclass(frozen=True)
class MetricSpec:
    key: str
    name: str
    category: str
    description: str
    value_type: MetricValueType
    higher_is_better: bool
    compute: Callable[[MetricInput], float]

    def as_definition_kwargs(self) -> dict:
        return {
            "key": self.key, "name": self.name, "category": self.category, "description": self.description,
            "value_type": self.value_type.value, "higher_is_better": self.higher_is_better,
        }


METRIC_SPECS: list[MetricSpec] = [
    MetricSpec("accuracy", "Accuracy", MetricCategory.ACCURACY.value, "Exact-match agreement between actual and expected output.", MetricValueType.NUMERIC, True, fn.accuracy),
    MetricSpec("precision", "Precision", MetricCategory.PRECISION.value, "Fraction of actual-output tokens that appear in the expected output.", MetricValueType.NUMERIC, True, fn.precision),
    MetricSpec("recall", "Recall", MetricCategory.RECALL.value, "Fraction of expected-output tokens present in the actual output.", MetricValueType.NUMERIC, True, fn.recall),
    MetricSpec("f1_score", "F1 Score", MetricCategory.F1_SCORE.value, "Harmonic mean of precision and recall.", MetricValueType.NUMERIC, True, fn.f1_score),
    MetricSpec("task_success_rate", "Task Success Rate", MetricCategory.TASK_SUCCESS_RATE.value, "Whether the task was completed successfully.", MetricValueType.NUMERIC, True, fn.task_success_rate),
    MetricSpec("reasoning_quality", "Reasoning Quality", MetricCategory.REASONING_QUALITY.value, "Token-overlap similarity between produced and expected reasoning steps.", MetricValueType.NUMERIC, True, fn.reasoning_quality),
    MetricSpec("planning_quality", "Planning Quality", MetricCategory.PLANNING_QUALITY.value, "Jaccard similarity between produced and expected plan steps.", MetricValueType.NUMERIC, True, fn.planning_quality),
    MetricSpec("groundedness", "Groundedness", MetricCategory.GROUNDEDNESS.value, "Fraction of output content tokens that appear in the supplied context documents (lexical overlap).", MetricValueType.NUMERIC, True, fn.groundedness),
    MetricSpec("faithfulness", "Faithfulness", MetricCategory.FAITHFULNESS.value, "Fraction of output sentences individually supported by the context documents.", MetricValueType.NUMERIC, True, fn.faithfulness),
    MetricSpec("hallucination_rate", "Hallucination Rate", MetricCategory.HALLUCINATION_RATE.value, "1 - groundedness; the fraction of output content not traceable to context.", MetricValueType.NUMERIC, False, fn.hallucination_rate),
    MetricSpec("citation_quality", "Citation Quality", MetricCategory.CITATION_QUALITY.value, "Fraction of [n]-style citations in the output that reference a valid context document.", MetricValueType.NUMERIC, True, fn.citation_quality),
    MetricSpec("response_completeness", "Response Completeness", MetricCategory.RESPONSE_COMPLETENESS.value, "Fraction of expected-output content covered by the actual output.", MetricValueType.NUMERIC, True, fn.response_completeness),
    MetricSpec("instruction_following", "Instruction Following", MetricCategory.INSTRUCTION_FOLLOWING.value, "Fraction of given instructions whose keywords are reflected in the output.", MetricValueType.NUMERIC, True, fn.instruction_following),
    MetricSpec("consistency", "Consistency", MetricCategory.CONSISTENCY.value, "Average pairwise similarity across repeated outputs for the same input.", MetricValueType.NUMERIC, True, fn.consistency),
    MetricSpec("formatting_compliance", "Formatting Compliance", MetricCategory.FORMATTING_COMPLIANCE.value, "Whether the output matches the expected format (json or a regex pattern).", MetricValueType.BOOLEAN, True, fn.formatting_compliance),
    MetricSpec("json_validation", "JSON Validation", MetricCategory.JSON_VALIDATION.value, "Whether the output parses as JSON and contains any required keys.", MetricValueType.BOOLEAN, True, fn.json_validation),
    MetricSpec("latency", "Latency", MetricCategory.LATENCY.value, "Measured latency in milliseconds.", MetricValueType.NUMERIC, False, fn.latency),
    MetricSpec("token_usage", "Token Usage", MetricCategory.TOKEN_USAGE.value, "Total prompt + completion tokens consumed.", MetricValueType.NUMERIC, False, fn.token_usage),
    MetricSpec("cost", "Cost", MetricCategory.COST.value, "Measured execution cost.", MetricValueType.NUMERIC, False, fn.cost),
    MetricSpec("reliability", "Reliability", MetricCategory.RELIABILITY.value, "Success rate discounted by the number of retries needed.", MetricValueType.NUMERIC, True, fn.reliability),
]

_BY_KEY = {spec.key: spec for spec in METRIC_SPECS}


def get_metric_spec(key: str):
    from eval_platform.core.exceptions import UnknownMetricError

    spec = _BY_KEY.get(key)
    if spec is None:
        raise UnknownMetricError(f"unknown metric key '{key}'")
    return spec
