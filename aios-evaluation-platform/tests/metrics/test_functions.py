import pytest

from eval_platform.core.exceptions import MetricComputationError
from eval_platform.metrics import functions as fn
from eval_platform.metrics.inputs import MetricInput


def test_accuracy_exact_match():
    assert fn.accuracy(MetricInput(actual_output="Paris", expected_output="paris ")) == 1.0
    assert fn.accuracy(MetricInput(actual_output="Paris", expected_output="London")) == 0.0


def test_accuracy_requires_both_fields():
    with pytest.raises(MetricComputationError):
        fn.accuracy(MetricInput(actual_output="Paris"))


def test_precision_recall_f1():
    i = MetricInput(actual_output="the cat sat on the mat", expected_output="the cat sat")
    p, r, f1 = fn.precision(i), fn.recall(i), fn.f1_score(i)
    assert 0.0 < p < 1.0
    assert r == 1.0
    assert 0.0 < f1 < 1.0


def test_task_success_rate():
    assert fn.task_success_rate(MetricInput(success=True)) == 1.0
    assert fn.task_success_rate(MetricInput(success=False)) == 0.0
    with pytest.raises(MetricComputationError):
        fn.task_success_rate(MetricInput())


def test_reasoning_quality_overlap():
    i = MetricInput(reasoning_steps=["check the database", "return result"], expected_reasoning_steps=["check the database", "return result"])
    assert fn.reasoning_quality(i) == 1.0


def test_planning_quality_partial_overlap():
    i = MetricInput(plan_steps=["step1", "step2"], expected_plan_steps=["step1", "step3"])
    score = fn.planning_quality(i)
    assert 0.0 < score < 1.0


def test_reliability_penalizes_retries():
    assert fn.reliability(MetricInput(success=True, retry_count=0)) == 1.0
    assert fn.reliability(MetricInput(success=True, retry_count=1)) == 0.5
    assert fn.reliability(MetricInput(success=False, retry_count=2)) == 0.0
    with pytest.raises(MetricComputationError):
        fn.reliability(MetricInput(success=True, retry_count=-1))


def test_groundedness_and_hallucination_rate():
    i = MetricInput(actual_output="The capital of France is Paris", context_documents=["Paris is the capital city of France."])
    g = fn.groundedness(i)
    h = fn.hallucination_rate(i)
    assert 0.0 < g <= 1.0
    assert round(g + h, 6) == 1.0


def test_groundedness_requires_context():
    with pytest.raises(MetricComputationError):
        fn.groundedness(MetricInput(actual_output="something"))


def test_faithfulness_sentence_level():
    i = MetricInput(
        actual_output="Paris is the capital of France. Bananas grow on the moon.",
        context_documents=["Paris is the capital of France."],
    )
    score = fn.faithfulness(i)
    assert 0.0 < score < 1.0


def test_citation_quality_valid_and_invalid():
    i = MetricInput(actual_output="This is supported [1] and this too [2] but not this [9].", context_documents=["doc a", "doc b"])
    score = fn.citation_quality(i)
    assert round(score, 4) == round(2 / 3, 4)


def test_citation_quality_no_citations_returns_zero():
    i = MetricInput(actual_output="No citations here.", context_documents=["doc a"])
    assert fn.citation_quality(i) == 0.0


def test_response_completeness_is_recall():
    i = MetricInput(actual_output="cat sat", expected_output="cat sat mat")
    assert fn.response_completeness(i) == fn.recall(i)


def test_instruction_following():
    i = MetricInput(actual_output="Respond in JSON with a summary field.", instructions=["respond in json", "include a summary"])
    score = fn.instruction_following(i)
    assert score == 1.0


def test_consistency_across_repeated_outputs():
    i = MetricInput(repeated_outputs=["the answer is 42", "the answer is 42", "completely different text"])
    score = fn.consistency(i)
    assert 0.0 < score < 1.0

    with pytest.raises(MetricComputationError):
        fn.consistency(MetricInput(repeated_outputs=["only one"]))


def test_formatting_compliance_json_and_regex():
    assert fn.formatting_compliance(MetricInput(actual_output='{"a": 1}', expected_format="json")) == 1.0
    assert fn.formatting_compliance(MetricInput(actual_output="not json", expected_format="json")) == 0.0
    assert fn.formatting_compliance(MetricInput(actual_output="order-1234", expected_format=r"regex:^order-\d+$")) == 1.0
    with pytest.raises(MetricComputationError):
        fn.formatting_compliance(MetricInput(actual_output="x", expected_format="yaml"))


def test_json_validation_with_required_keys():
    assert fn.json_validation(MetricInput(actual_output='{"a": 1, "b": 2}', json_schema_required_keys=["a", "b"])) == 1.0
    assert fn.json_validation(MetricInput(actual_output='{"a": 1}', json_schema_required_keys=["a", "b"])) == 0.0
    assert fn.json_validation(MetricInput(actual_output="not json")) == 0.0


def test_latency_token_usage_cost():
    assert fn.latency(MetricInput(latency_ms=123.4)) == 123.4
    with pytest.raises(MetricComputationError):
        fn.latency(MetricInput(latency_ms=-1))

    assert fn.token_usage(MetricInput(prompt_tokens=10, completion_tokens=5)) == 15.0
    with pytest.raises(MetricComputationError):
        fn.token_usage(MetricInput())

    assert fn.cost(MetricInput(cost=0.02)) == 0.02
    with pytest.raises(MetricComputationError):
        fn.cost(MetricInput(cost=-0.01))
