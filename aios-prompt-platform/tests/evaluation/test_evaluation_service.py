import pytest

from prompt_platform.domain.enums import EvalMetric
from prompt_platform.models.prompt import PromptModel
from prompt_platform.models.version import PromptVersionModel
from prompt_platform.models.workspace import PromptProjectModel, PromptWorkspaceModel
from prompt_platform.prompt_evaluation.evaluation_service import EvaluationService
from prompt_platform.prompt_evaluation.rule_based_metrics import score_cost, score_formatting, score_latency, score_token_usage

from tests.conftest import make_response


async def _seed_prompt_version(repos, *, user_template="Answer: {{q}}", parameters=None):
    ws = await repos.workspaces.add(PromptWorkspaceModel(name="WS", slug="ws", organization_id="org1"))
    proj = await repos.projects.add(PromptProjectModel(workspace_id=ws.id, name="Proj", slug="proj"))
    prompt = await repos.prompts.add(PromptModel(project_id=proj.id, workspace_id=ws.id, name="QA", slug="qa", owner_id="u1"))
    version = await repos.versions.add(
        PromptVersionModel(prompt_id=prompt.id, version_number=1, user_template=user_template, parameters=parameters or {"model": "m1", "provider": "test"})
    )
    return prompt, version


def test_score_latency_falloff():
    assert score_latency(500, target_ms=2000) == 100.0
    assert score_latency(2000, target_ms=2000) == 100.0
    assert score_latency(6000, target_ms=2000) == 0.0
    mid = score_latency(4000, target_ms=2000)
    assert 0 < mid < 100


def test_score_cost_and_token_usage_falloff():
    assert score_cost(0.001, budget_usd=0.01) == 100.0
    assert score_token_usage(500, budget_tokens=1000) == 100.0


def test_score_formatting_valid_and_invalid_json():
    assert score_formatting('{"a": 1}', expect_json=True) == 100.0
    assert score_formatting("not json", expect_json=True) == 0.0
    assert score_formatting("anything", expect_json=False) == 100.0


@pytest.mark.asyncio
async def test_run_automatic_with_rule_based_metrics_only(repos, scripted_ai_core):
    context, provider = scripted_ai_core
    prompt, version = await _seed_prompt_version(repos)
    provider.push(make_response("Answer: 4"))

    svc = EvaluationService(repos, context)
    run = await svc.run_automatic(
        prompt.id, version.id, test_inputs=[{"q": "2+2"}], metrics=[EvalMetric.LATENCY, EvalMetric.COST], triggered_by="u1"
    )
    assert run.status == "completed"
    assert "latency" in run.summary["metric_scores"]
    assert "cost" in run.summary["metric_scores"]


@pytest.mark.asyncio
async def test_run_automatic_with_llm_judge_metric(repos, scripted_ai_core):
    context, provider = scripted_ai_core
    prompt, version = await _seed_prompt_version(repos)
    provider.push(make_response("Answer: 4"))  # the actual generation
    provider.push(make_response('{"score": 90, "rationale": "correct and complete"}'))  # the judge call

    svc = EvaluationService(repos, context)
    run = await svc.run_automatic(prompt.id, version.id, test_inputs=[{"q": "2+2"}], metrics=[EvalMetric.ACCURACY], triggered_by="u1", persist_eval_score=True)
    assert run.summary["metric_scores"]["accuracy"] == 90.0
    assert run.summary["overall_score"] == 90.0

    refreshed_version = await repos.versions.get(version.id)
    assert refreshed_version.eval_score == 90.0


@pytest.mark.asyncio
async def test_run_human_review_persists_user_rating(repos, scripted_ai_core):
    context, _ = scripted_ai_core
    prompt, version = await _seed_prompt_version(repos)
    svc = EvaluationService(repos, context)
    run = await svc.run_human_review(prompt.id, version.id, reviewer_id="reviewer1", score=75.0, rationale="mostly good")
    results = await svc.get_results(run.id)
    assert results[0].metric_name == "user_rating"
    assert results[0].score == 75.0


@pytest.mark.asyncio
async def test_run_pairwise_picks_higher_scoring_version(repos, scripted_ai_core):
    context, provider = scripted_ai_core
    prompt, version_a = await _seed_prompt_version(repos, user_template="v1: {{q}}")
    _, version_b = await _seed_prompt_version(repos, user_template="v2: {{q}}")

    provider.push(make_response("A's answer"))
    provider.push(make_response("B's answer"))
    provider.push(make_response('{"score": 60, "rationale": "ok"}'))   # judge for A
    provider.push(make_response('{"score": 95, "rationale": "great"}'))  # judge for B

    svc = EvaluationService(repos, context)
    run = await svc.run_pairwise(prompt.id, version_a.id, version_b.id, variables={"q": "2+2"}, triggered_by="u1")
    assert run.summary["preference_for_a"] == 0.0
    assert run.summary["score_b"] == 95


@pytest.mark.asyncio
async def test_run_benchmark_compares_multiple_versions(repos, scripted_ai_core):
    context, provider = scripted_ai_core
    prompt, version_a = await _seed_prompt_version(repos, user_template="v1: {{q}}")
    _, version_b = await _seed_prompt_version(repos, user_template="v2: {{q}}")

    provider.push(make_response("answer A"))
    provider.push(make_response("answer B"))

    svc = EvaluationService(repos, context)
    comparison = await svc.run_benchmark(
        prompt.id, [version_a.id, version_b.id], test_inputs=[{"q": "2+2"}], metrics=[EvalMetric.LATENCY], triggered_by="u1"
    )
    assert set(comparison.keys()) == {version_a.id, version_b.id}
    assert "overall_score" in comparison[version_a.id]
