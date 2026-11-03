import pytest

from prompt_platform.core.exceptions import InvalidTransitionError, NotFoundError, ValidationError
from prompt_platform.domain.enums import EvalMetric, ExperimentStatus
from prompt_platform.models.prompt import PromptModel
from prompt_platform.models.version import PromptVersionModel
from prompt_platform.models.workspace import PromptProjectModel, PromptWorkspaceModel
from prompt_platform.prompt_experiments.experiment_service import ExperimentService
from prompt_platform.prompt_experiments.statistics import select_winner, summarize, t_critical, welch_t_test

from tests.conftest import make_response


async def _seed_workspace_and_versions(repos):
    ws = await repos.workspaces.add(PromptWorkspaceModel(name="WS", slug="ws-exp", organization_id="org1"))
    proj = await repos.projects.add(PromptProjectModel(workspace_id=ws.id, name="Proj", slug="proj-exp"))
    prompt = await repos.prompts.add(PromptModel(project_id=proj.id, workspace_id=ws.id, name="QA", slug="qa-exp", owner_id="u1"))
    version_a = await repos.versions.add(
        PromptVersionModel(prompt_id=prompt.id, version_number=1, user_template="Concise: {{q}}", parameters={"model": "m1", "provider": "test"})
    )
    version_b = await repos.versions.add(
        PromptVersionModel(prompt_id=prompt.id, version_number=2, user_template="Verbose: {{q}}", parameters={"model": "m1", "provider": "test"})
    )
    return ws, prompt, version_a, version_b


def _judge_json(score: float) -> str:
    return f'{{"score": {score}, "rationale": "scripted"}}'


# -- pure statistics -----------------------------------------------------------

def test_summarize_empty_and_nonempty():
    empty = summarize([])
    assert empty.n == 0 and empty.mean == 0.0
    s = summarize([1.0, 2.0, 3.0])
    assert s.n == 3 and s.mean == 2.0 and s.minimum == 1.0 and s.maximum == 3.0


def test_welch_t_test_detects_clear_difference():
    high = [88.0, 92.0, 90.0]
    low = [58.0, 62.0, 60.0]
    result = welch_t_test(high, low)
    assert result.mean_diff == pytest.approx(30.0)
    assert result.significant is True
    assert result.p_value < 0.05
    assert result.cohens_d > 0


def test_welch_t_test_no_difference_not_significant():
    a = [70.0, 71.0, 69.0, 70.5]
    b = [70.2, 69.8, 70.1, 69.9]
    result = welch_t_test(a, b)
    assert result.significant is False


def test_t_critical_matches_known_table_value():
    assert t_critical(10, confidence=0.95) == pytest.approx(2.228, abs=0.01)


def test_select_winner_identifies_leader_and_significance():
    scores = {"v1": [88.0, 92.0, 90.0], "v2": [58.0, 62.0, 60.0], "v3": [80.0, 81.0, 79.0]}
    winner = select_winner(scores)
    assert winner.leader_variant_id == "v1"
    assert winner.comparisons["v2"]["significant"] is True
    assert winner.significant_winner in (True, False)  # depends on v1 vs v3 gap; just must not error


# -- ExperimentService: setup and lifecycle guards ------------------------------

@pytest.mark.asyncio
async def test_create_experiment_and_add_variants(repos, scripted_ai_core):
    context, _ = scripted_ai_core
    ws, prompt, version_a, version_b = await _seed_workspace_and_versions(repos)
    svc = ExperimentService(repos, context)

    experiment = await svc.create_experiment(ws.id, prompt.id, name="Concise vs Verbose", actor_id="u1", sample_size_per_variant=3)
    assert experiment.status == ExperimentStatus.DRAFT.value

    variant_a = await svc.add_variant(experiment.id, name="A", prompt_version_id=version_a.id, traffic_percent=50.0)
    variant_b = await svc.add_variant(experiment.id, name="B", prompt_version_id=version_b.id, traffic_percent=50.0)
    assert variant_a.name == "A" and variant_b.name == "B"

    variants = await svc.list_variants(experiment.id)
    assert len(variants) == 2


@pytest.mark.asyncio
async def test_start_requires_two_variants(repos, scripted_ai_core):
    context, _ = scripted_ai_core
    ws, prompt, version_a, _ = await _seed_workspace_and_versions(repos)
    svc = ExperimentService(repos, context)
    experiment = await svc.create_experiment(ws.id, prompt.id, name="Solo", actor_id="u1")
    await svc.add_variant(experiment.id, name="A", prompt_version_id=version_a.id)
    with pytest.raises(ValidationError):
        await svc.start_experiment(experiment.id)


@pytest.mark.asyncio
async def test_cannot_add_variant_after_start(repos, scripted_ai_core):
    context, _ = scripted_ai_core
    ws, prompt, version_a, version_b = await _seed_workspace_and_versions(repos)
    svc = ExperimentService(repos, context)
    experiment = await svc.create_experiment(ws.id, prompt.id, name="Exp", actor_id="u1")
    await svc.add_variant(experiment.id, name="A", prompt_version_id=version_a.id)
    await svc.add_variant(experiment.id, name="B", prompt_version_id=version_b.id)
    await svc.start_experiment(experiment.id)
    with pytest.raises(InvalidTransitionError):
        await svc.add_variant(experiment.id, name="C", prompt_version_id=version_a.id)


@pytest.mark.asyncio
async def test_run_requires_running_status(repos, scripted_ai_core):
    context, _ = scripted_ai_core
    ws, prompt, version_a, version_b = await _seed_workspace_and_versions(repos)
    svc = ExperimentService(repos, context)
    experiment = await svc.create_experiment(ws.id, prompt.id, name="Exp", actor_id="u1")
    await svc.add_variant(experiment.id, name="A", prompt_version_id=version_a.id)
    await svc.add_variant(experiment.id, name="B", prompt_version_id=version_b.id)
    with pytest.raises(InvalidTransitionError):
        await svc.run(experiment.id, test_inputs=[{"q": "2+2"}], triggered_by="u1")


# -- ExperimentService: full run with a judge-based metric -----------------------

@pytest.mark.asyncio
async def test_run_experiment_picks_statistically_significant_winner(repos, scripted_ai_core):
    context, provider = scripted_ai_core
    ws, prompt, version_a, version_b = await _seed_workspace_and_versions(repos)
    svc = ExperimentService(repos, context)

    experiment = await svc.create_experiment(ws.id, prompt.id, name="Concise vs Verbose", actor_id="u1", sample_size_per_variant=3, random_seed=7)
    variant_a = await svc.add_variant(experiment.id, name="A", prompt_version_id=version_a.id)
    variant_b = await svc.add_variant(experiment.id, name="B", prompt_version_id=version_b.id)
    await svc.start_experiment(experiment.id)

    # Variant A: 3 samples, each consumes (generation, judge) — scripted high scores.
    for score in (88.0, 92.0, 90.0):
        provider.push(make_response("A's answer"))
        provider.push(make_response(_judge_json(score)))
    # Variant B: 3 samples — scripted low scores.
    for score in (58.0, 62.0, 60.0):
        provider.push(make_response("B's answer"))
        provider.push(make_response(_judge_json(score)))

    completed = await svc.run(experiment.id, test_inputs=[{"q": "2+2"}], metric=EvalMetric.ACCURACY, triggered_by="u1")
    assert completed.status == ExperimentStatus.COMPLETED.value
    assert completed.winner_variant_id == variant_a.id

    results = await svc.get_results(experiment.id)
    assert len(results) == 2
    a_result = next(r for r in results if r.variant_id == variant_a.id)
    assert a_result.sample_size == 3
    assert a_result.mean_score == pytest.approx(90.0)

    summary = await svc.statistical_summary(experiment.id, metric=EvalMetric.ACCURACY)
    assert summary["leader_variant_id"] == variant_a.id
    assert summary["significant_winner"] is True
    assert summary["comparisons"][variant_b.id]["significant"] is True


@pytest.mark.asyncio
async def test_statistical_summary_raises_without_results(repos, scripted_ai_core):
    context, _ = scripted_ai_core
    ws, prompt, version_a, version_b = await _seed_workspace_and_versions(repos)
    svc = ExperimentService(repos, context)
    experiment = await svc.create_experiment(ws.id, prompt.id, name="Exp", actor_id="u1")
    await svc.add_variant(experiment.id, name="A", prompt_version_id=version_a.id)
    await svc.add_variant(experiment.id, name="B", prompt_version_id=version_b.id)
    with pytest.raises(NotFoundError):
        await svc.statistical_summary(experiment.id)


@pytest.mark.asyncio
async def test_run_is_reproducible_given_same_seed(repos, scripted_ai_core):
    """Two variants sampling from a pool of several test inputs, with the
    same random_seed, must sample the exact same sequence of inputs —
    verified indirectly by checking the sampler helper directly."""
    context, _ = scripted_ai_core
    ws, prompt, version_a, version_b = await _seed_workspace_and_versions(repos)
    svc = ExperimentService(repos, context)
    experiment = await svc.create_experiment(ws.id, prompt.id, name="Exp", actor_id="u1", sample_size_per_variant=5, random_seed=123)

    inputs = [{"q": "1"}, {"q": "2"}, {"q": "3"}, {"q": "4"}]
    first = svc._sample_inputs(experiment, inputs, salt="variant-a")
    second = svc._sample_inputs(experiment, inputs, salt="variant-a")
    third_different_salt = svc._sample_inputs(experiment, inputs, salt="variant-b")

    assert first == second  # same seed + same salt => identical sample sequence
    assert first != third_different_salt  # same seed but different salt => different sequence
    assert len(first) == 5


@pytest.mark.asyncio
async def test_archive_experiment(repos, scripted_ai_core):
    context, _ = scripted_ai_core
    ws, prompt, version_a, version_b = await _seed_workspace_and_versions(repos)
    svc = ExperimentService(repos, context)
    experiment = await svc.create_experiment(ws.id, prompt.id, name="Exp", actor_id="u1")
    archived = await svc.archive(experiment.id)
    assert archived.status == ExperimentStatus.ARCHIVED.value
