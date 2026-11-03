import pytest

from prompt_platform.models.prompt import PromptModel
from prompt_platform.models.version import PromptVersionModel
from prompt_platform.models.workspace import PromptProjectModel, PromptWorkspaceModel
from prompt_platform.prompt_evaluation.evaluation_service import EvaluationService
from prompt_platform.prompt_observability.observability_service import ObservabilityService
from prompt_platform.prompt_testing.test_service import PromptTestingService

from ai_core.utils.exceptions import AllProvidersFailedError

from tests.conftest import make_response


async def _seed_prompt_version(repos, *, user_template="Answer {{q}}."):
    ws = await repos.workspaces.add(PromptWorkspaceModel(name="WS", slug="ws-obs", organization_id="org1"))
    proj = await repos.projects.add(PromptProjectModel(workspace_id=ws.id, name="Proj", slug="proj-obs"))
    prompt = await repos.prompts.add(PromptModel(project_id=proj.id, workspace_id=ws.id, name="QA", slug="qa-obs", owner_id="u1"))
    version = await repos.versions.add(
        PromptVersionModel(prompt_id=prompt.id, version_number=1, user_template=user_template, parameters={"model": "m1", "provider": "test"})
    )
    return prompt, version


@pytest.mark.asyncio
async def test_running_a_test_case_writes_an_execution_log(repos, scripted_ai_core):
    context, provider = scripted_ai_core
    prompt, version = await _seed_prompt_version(repos)
    provider.push(make_response("4"))

    testing_svc = PromptTestingService(repos, context)
    await testing_svc.run_single(prompt.id, version.id, variables={"q": "2+2"}, expected_output="4", triggered_by="u1")

    obs = ObservabilityService(repos)
    history = await obs.execution_history(prompt.id)
    assert len(history) == 1
    assert history[0].source == "test"
    assert history[0].success is True
    assert history[0].model_used == "m1"


@pytest.mark.asyncio
async def test_failed_execution_is_logged_with_error(repos, scripted_ai_core):
    context, provider = scripted_ai_core
    prompt, version = await _seed_prompt_version(repos)
    # The ExecutionEngine wraps any provider failure (after retries/fallback
    # across candidates are exhausted) as AllProvidersFailedError — the
    # observability log should still record it as a failed execution.
    provider.push(RuntimeError("provider exploded"))

    testing_svc = PromptTestingService(repos, context)
    with pytest.raises(AllProvidersFailedError):
        await testing_svc.run_single(prompt.id, version.id, variables={"q": "2+2"}, triggered_by="u1")

    obs = ObservabilityService(repos)
    history = await obs.execution_history(prompt.id)
    assert len(history) == 1
    assert history[0].success is False
    assert "candidate(s) failed" in history[0].error_message


@pytest.mark.asyncio
async def test_analytics_summary_computes_rollups(repos, scripted_ai_core):
    context, provider = scripted_ai_core
    prompt, version = await _seed_prompt_version(repos)
    for _ in range(3):
        provider.push(make_response("ok"))
    provider.push(RuntimeError("boom"))

    testing_svc = PromptTestingService(repos, context)
    for _ in range(3):
        await testing_svc.run_single(prompt.id, version.id, variables={"q": "x"}, triggered_by="u1")
    with pytest.raises(AllProvidersFailedError):
        await testing_svc.run_single(prompt.id, version.id, variables={"q": "x"}, triggered_by="u1")

    obs = ObservabilityService(repos)
    summary = await obs.analytics_summary(prompt.id)
    assert summary["total_executions"] == 4
    assert summary["failure_count"] == 1
    assert summary["success_rate"] == 75.0
    assert summary["model_breakdown"] == {"m1": 3}
    assert summary["source_breakdown"] == {"test": 4}
    assert summary["latency_ms"]["avg"] >= 0
    assert "candidate(s) failed" in summary["top_failure_reasons"][0][0]


@pytest.mark.asyncio
async def test_analytics_summary_empty_prompt_returns_zeros(repos, scripted_ai_core):
    context, _ = scripted_ai_core
    prompt, version = await _seed_prompt_version(repos)
    obs = ObservabilityService(repos)
    summary = await obs.analytics_summary(prompt.id)
    assert summary["total_executions"] == 0
    assert summary["success_rate"] == 0.0


@pytest.mark.asyncio
async def test_record_user_feedback(repos, scripted_ai_core):
    context, provider = scripted_ai_core
    prompt, version = await _seed_prompt_version(repos)
    provider.push(make_response("ok"))
    testing_svc = PromptTestingService(repos, context)
    await testing_svc.run_single(prompt.id, version.id, variables={"q": "x"}, triggered_by="u1")

    obs = ObservabilityService(repos)
    log = (await obs.execution_history(prompt.id))[0]
    updated = await obs.record_user_feedback(log.id, 4.5)
    assert updated.user_feedback_score == 4.5

    summary = await obs.analytics_summary(prompt.id)
    assert summary["avg_user_feedback_score"] == 4.5


@pytest.mark.asyncio
async def test_evaluation_runs_are_also_logged(repos, scripted_ai_core):
    context, provider = scripted_ai_core
    prompt, version = await _seed_prompt_version(repos)
    provider.push(make_response("4"))
    provider.push(make_response('{"score": 90, "rationale": "good"}'))

    eval_svc = EvaluationService(repos, context)
    from prompt_platform.domain.enums import EvalMetric
    await eval_svc.run_automatic(prompt.id, version.id, test_inputs=[{"q": "2+2"}], metrics=[EvalMetric.ACCURACY], triggered_by="u1")

    obs = ObservabilityService(repos)
    history = await obs.execution_history(prompt.id)
    assert len(history) == 1
    assert history[0].source == "evaluation"
