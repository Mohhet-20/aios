import pytest

from prompt_platform.domain.enums import OptimizationObjective
from prompt_platform.models.prompt import PromptModel
from prompt_platform.models.version import PromptVersionModel
from prompt_platform.models.workspace import PromptProjectModel, PromptWorkspaceModel
from prompt_platform.prompt_engine.versioning_service import VersioningService
from prompt_platform.prompt_optimization import heuristics
from prompt_platform.prompt_optimization.few_shot import build_few_shot_block, select_few_shot_examples
from prompt_platform.prompt_optimization.optimization_service import OptimizationService
from prompt_platform.prompt_testing.test_service import PromptTestingService

from tests.conftest import make_response


async def _seed_prompt_version(repos, *, user_template="Please answer {{q}} in an appropriate way.", parameters=None):
    ws = await repos.workspaces.add(PromptWorkspaceModel(name="WS", slug="ws-opt", organization_id="org1"))
    proj = await repos.projects.add(PromptProjectModel(workspace_id=ws.id, name="Proj", slug="proj-opt"))
    prompt = await repos.prompts.add(PromptModel(project_id=proj.id, workspace_id=ws.id, name="QA", slug="qa-opt", owner_id="u1"))
    version = await repos.versions.add(
        PromptVersionModel(
            prompt_id=prompt.id, version_number=1, user_template=user_template,
            variables_schema=[{"name": "q"}], parameters=parameters or {"model": "m1", "provider": "test"},
        )
    )
    # Keep the prompt aggregate's version counter in sync so that any later
    # VersioningService.create_version() call (e.g. from apply=True flows)
    # numbers the next version correctly instead of colliding with #1.
    prompt.latest_version_number = 1
    prompt = await repos.prompts.update(prompt)
    return prompt, version


# -- pure heuristics ---------------------------------------------------------

def test_find_vague_terms_detects_qualifiers():
    assert "appropriate" in heuristics.find_vague_terms("Answer in an appropriate way, properly.")
    assert heuristics.find_vague_terms("Return the sum of the two integers as JSON.") == []


def test_has_output_format_guidance():
    assert heuristics.has_output_format_guidance("Respond with JSON containing a 'result' field.")
    assert not heuristics.has_output_format_guidance("Tell me a joke.")


def test_has_few_shot_examples():
    assert heuristics.has_few_shot_examples("Example: input=2, output=4.")
    assert not heuristics.has_few_shot_examples("Just answer the question.")


def test_variable_usage_report_flags_mismatch():
    class FakeVersion:
        system_template = None
        developer_template = None
        user_template = "Answer {{q}} using {{context}}."
        variables_schema = [{"name": "q"}, {"name": "unused_var"}]

    report = heuristics.variable_usage_report(FakeVersion())
    assert report["unused_declared"] == ["unused_var"]
    assert report["undeclared_used"] == ["context"]


def test_select_few_shot_examples_prefers_passing_cases():
    class Case:
        def __init__(self, id, name, expected_output):
            self.id, self.name, self.expected_output = id, name, expected_output
            self.input_variables = {"q": id}

    class Result:
        def __init__(self, golden_test_case_id, passed):
            self.golden_test_case_id, self.passed = golden_test_case_id, passed

    cases = [Case("c1", "case1", "4"), Case("c2", "case2", "6"), Case("c3", "case3", None)]
    results = [Result("c1", False), Result("c2", True)]
    selected = select_few_shot_examples(cases, results, max_examples=2)
    assert [c.id for c in selected] == ["c2", "c1"]  # passing case ranked first; case3 excluded (no expected_output)

    block = build_few_shot_block(selected)
    assert "Example 1" in block and "Example 2" in block


# -- OptimizationService: rule-based suggest() --------------------------------

@pytest.mark.asyncio
async def test_suggest_flags_clarity_format_and_few_shot_gaps(repos, scripted_ai_core):
    context, _ = scripted_ai_core
    prompt, version = await _seed_prompt_version(repos)
    svc = OptimizationService(repos, context)

    run = await svc.suggest(prompt.id, version.id, objective=OptimizationObjective.QUALITY, triggered_by="u1")
    assert run.status == "completed"
    categories = {s for s in run.summary["categories"]}
    assert "instruction_clarity" in categories
    assert "response_formatting" in categories
    assert "few_shot_examples" in categories

    suggestions = await svc.get_suggestions(run.id)
    assert len(suggestions) == run.summary["suggestion_count"]


@pytest.mark.asyncio
async def test_suggest_flags_variable_mismatch(repos, scripted_ai_core):
    context, _ = scripted_ai_core
    prompt, version = await _seed_prompt_version(repos, user_template="Answer {{q}} using {{missing_var}}. Respond in JSON. Example: input=1, output=2.")
    version.variables_schema = [{"name": "q"}, {"name": "unused_var"}]
    version = await repos.versions.update(version)

    svc = OptimizationService(repos, context)
    run = await svc.suggest(prompt.id, version.id, triggered_by="u1")
    suggestions = await svc.get_suggestions(run.id)
    var_suggestion = next(s for s in suggestions if s.category == "variable_usage")
    assert "missing_var" in var_suggestion.rationale
    assert "unused_var" in var_suggestion.rationale


@pytest.mark.asyncio
async def test_suggest_flags_compression_candidate_and_ranks_first_for_cost_objective(repos, scripted_ai_core):
    context, _ = scripted_ai_core
    long_template = ("Please carefully answer the following question: {{q}}. " * 80)
    prompt, version = await _seed_prompt_version(repos, user_template=long_template)

    svc = OptimizationService(repos, context)
    run = await svc.suggest(prompt.id, version.id, objective=OptimizationObjective.COST, triggered_by="u1")
    suggestions = await svc.get_suggestions(run.id)
    assert any(s.category == "compression" for s in suggestions)
    # Efficiency-first ordering ranks compression first for a COST objective.
    categories_in_order = [s.category for s in suggestions]
    assert categories_in_order[0] == "compression"
    assert categories_in_order.index("compression") < categories_in_order.index("few_shot_examples")


# -- OptimizationService: LLM-backed auto_optimize() ---------------------------

@pytest.mark.asyncio
async def test_auto_optimize_quality_applies_new_version(repos, scripted_ai_core):
    context, provider = scripted_ai_core
    prompt, version = await _seed_prompt_version(repos)
    provider.push(make_response("Answer the question {{q}} with a single, factually correct sentence."))

    svc = OptimizationService(repos, context, versioning_service=VersioningService(repos))
    run = await svc.auto_optimize(prompt.id, version.id, objective=OptimizationObjective.QUALITY, actor_id="u1", apply=True)

    assert run.status == "completed"
    assert run.result_version_id is not None
    new_version = await repos.versions.get(run.result_version_id)
    assert new_version.user_template == "Answer the question {{q}} with a single, factually correct sentence."
    assert new_version.parent_version_id == version.id
    assert new_version.version_number == 2

    suggestions = await svc.get_suggestions(run.id)
    assert suggestions[0].applied is True
    assert suggestions[0].category == "instruction_clarity"


@pytest.mark.asyncio
async def test_auto_optimize_cost_objective_compresses_without_applying(repos, scripted_ai_core):
    context, provider = scripted_ai_core
    prompt, version = await _seed_prompt_version(repos, user_template="Please answer {{q}} thoroughly and completely with lots of detail.")
    provider.push(make_response("Answer {{q}} briefly."))

    svc = OptimizationService(repos, context)
    run = await svc.auto_optimize(prompt.id, version.id, objective=OptimizationObjective.COST, actor_id="u1", apply=False)

    assert run.result_version_id is None
    suggestions = await svc.get_suggestions(run.id)
    assert suggestions[0].category == "compression"
    assert suggestions[0].applied is False
    assert suggestions[0].estimated_impact["token_delta"] < 0

    # No new version should have been created since apply=False.
    all_versions = await repos.versions.list_for_prompt(prompt.id)
    assert len(all_versions) == 1


@pytest.mark.asyncio
async def test_auto_optimize_raises_without_user_template(repos, scripted_ai_core):
    context, _ = scripted_ai_core
    prompt, version = await _seed_prompt_version(repos)
    version.user_template = ""
    await repos.versions.update(version)

    svc = OptimizationService(repos, context)
    from prompt_platform.core.exceptions import ValidationError
    with pytest.raises(ValidationError):
        await svc.auto_optimize(prompt.id, version.id, objective=OptimizationObjective.QUALITY, actor_id="u1")


# -- OptimizationService: few-shot optimization --------------------------------

@pytest.mark.asyncio
async def test_optimize_few_shot_selects_examples_and_applies(repos, scripted_ai_core):
    context, _ = scripted_ai_core
    prompt, version = await _seed_prompt_version(repos, user_template="Answer {{q}}.")
    testing_svc = PromptTestingService(repos, context)
    await testing_svc.create_golden_test_case(prompt.id, name="case1", input_variables={"q": "2+2"}, expected_output="4")
    await testing_svc.create_golden_test_case(prompt.id, name="case2", input_variables={"q": "3+3"}, expected_output="6")

    svc = OptimizationService(repos, context, versioning_service=VersioningService(repos))
    run = await svc.optimize_few_shot(prompt.id, version.id, actor_id="u1", max_examples=2, apply=True)

    assert run.result_version_id is not None
    new_version = await repos.versions.get(run.result_version_id)
    assert "Examples:" in new_version.user_template
    assert "case1" not in new_version.user_template  # block renders inputs/outputs, not case names
    assert "4" in new_version.user_template and "6" in new_version.user_template


@pytest.mark.asyncio
async def test_optimize_few_shot_no_eligible_cases_skips_apply(repos, scripted_ai_core):
    context, _ = scripted_ai_core
    prompt, version = await _seed_prompt_version(repos)

    svc = OptimizationService(repos, context)
    run = await svc.optimize_few_shot(prompt.id, version.id, actor_id="u1", apply=True)
    assert run.result_version_id is None
    suggestions = await svc.get_suggestions(run.id)
    assert suggestions[0].title == "No eligible golden test cases"


# -- apply_suggestion() applied independently of the originating call --------

@pytest.mark.asyncio
async def test_apply_suggestion_creates_new_version(repos, scripted_ai_core):
    context, provider = scripted_ai_core
    prompt, version = await _seed_prompt_version(repos)
    provider.push(make_response("Rewritten: answer {{q}} precisely."))

    svc = OptimizationService(repos, context, versioning_service=VersioningService(repos))
    run = await svc.auto_optimize(prompt.id, version.id, objective=OptimizationObjective.QUALITY, actor_id="u1", apply=False)
    suggestions = await svc.get_suggestions(run.id)
    assert suggestions[0].applied is False

    new_version = await svc.apply_suggestion(suggestions[0].id, "u2")
    assert new_version.user_template == "Rewritten: answer {{q}} precisely."

    refreshed_run = await repos.optimization_runs.get(run.id)
    assert refreshed_run.result_version_id == new_version.id
