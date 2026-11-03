import pytest

from tool_platform.ai_planning.models import ToolPlan
from tool_platform.core.exceptions import ToolPlanningError
from tests.ai_planning.conftest import make_published_tool


@pytest.mark.asyncio
async def test_match_capabilities_requires_all_of_them(planning_service, tool_service, version_service, workspace):
    await make_published_tool(
        tool_service, version_service, workspace, name="Slack Poster", category="notification",
        capabilities=["send_message", "network_access"],
    )
    await make_published_tool(
        tool_service, version_service, workspace, name="Email Sender", category="email",
        capabilities=["send_message"],
    )

    both = await planning_service.match_capabilities(workspace.id, ["send_message", "network_access"])
    assert len(both) == 1
    assert both[0].name == "Slack Poster"

    just_send = await planning_service.match_capabilities(workspace.id, ["send_message"])
    assert {t.name for t in just_send} == {"Slack Poster", "Email Sender"}


@pytest.mark.asyncio
async def test_validate_input_reports_schema_errors(planning_service, tool_service, version_service, workspace):
    tool = await make_published_tool(
        tool_service, version_service, workspace, name="Web Search", category="web_search",
        capabilities=["search"], input_schema={"type": "object", "required": ["query"], "properties": {"query": {"type": "string"}}},
    )
    version = await version_service.get_version(tool.current_version_id)

    error = await planning_service.validate_input(version.id, {"query": "hello"})
    assert error is None

    error = await planning_service.validate_input(version.id, {})
    assert error is not None
    assert "query" in error


@pytest.mark.asyncio
async def test_select_tool_raises_when_nothing_matches(planning_service, workspace):
    with pytest.raises(ToolPlanningError):
        await planning_service.select_tool(workspace.id, "nonexistent thing", required_capabilities=["teleportation"])


@pytest.mark.asyncio
async def test_select_tool_ranks_lexical_match_first(planning_service, tool_service, version_service, workspace):
    await make_published_tool(
        tool_service, version_service, workspace, name="GitHub Issue Creator", category="github",
        capabilities=["create_issue"], description="creates issues in a github repository",
    )
    await make_published_tool(
        tool_service, version_service, workspace, name="Slack Notifier", category="slack",
        capabilities=["send_message"], description="sends slack notifications",
    )

    ranked = await planning_service.select_tool(workspace.id, "create a github issue")
    assert ranked[0].name == "GitHub Issue Creator"


@pytest.mark.asyncio
async def test_resolve_fallback_chain_caps_length(planning_service):
    from tool_platform.ai_planning.models import RankedTool
    ranked = [RankedTool(tool_id=str(i), name=f"t{i}", category="c", score=1.0 - i * 0.01, reason="x") for i in range(10)]
    chain = planning_service.resolve_fallback_chain(ranked, max_fallbacks=2)
    assert len(chain) == 3
    assert chain[0] is ranked[0]


def test_build_plan_rejects_forward_reference(planning_service):
    with pytest.raises(ToolPlanningError):
        planning_service.build_plan([
            ("step_a", "tool-1", {"query": "$steps.step_b.result"}),
            ("step_b", "tool-2", {"q": "hello"}),
        ])


def test_build_plan_rejects_duplicate_step_id(planning_service):
    with pytest.raises(ToolPlanningError):
        planning_service.build_plan([
            ("step_a", "tool-1", {"q": "hello"}),
            ("step_a", "tool-2", {"q": "world"}),
        ])


def test_build_plan_and_resolve_step_input_composes_across_steps(planning_service):
    plan = planning_service.build_plan([
        ("search", "tool-search", {"query": "aios tool platform"}),
        ("summarize", "tool-summarize", {"text": "$steps.search.top_result.snippet", "max_words": 50}),
    ])
    assert isinstance(plan, ToolPlan)
    assert len(plan.steps) == 2

    step_outputs = {"search": {"top_result": {"snippet": "a great snippet", "url": "https://example.com"}}}
    resolved = planning_service.resolve_step_input(plan.steps[1], step_outputs)
    assert resolved == {"text": "a great snippet", "max_words": 50}


def test_resolve_step_input_raises_on_unresolvable_reference(planning_service):
    plan = planning_service.build_plan([
        ("search", "tool-search", {"query": "x"}),
        ("summarize", "tool-summarize", {"text": "$steps.search.missing_field"}),
    ])
    with pytest.raises(ToolPlanningError):
        planning_service.resolve_step_input(plan.steps[1], {"search": {"other_field": "value"}})


def test_optimize_plan_groups_independent_steps_into_same_wave(planning_service):
    plan = planning_service.build_plan([
        ("fetch_a", "tool-http", {"url": "https://a.example.com"}),
        ("fetch_b", "tool-http", {"url": "https://b.example.com"}),
        ("combine", "tool-combine", {"a": "$steps.fetch_a.body", "b": "$steps.fetch_b.body"}),
    ])
    waves = planning_service.optimize_plan(plan)
    assert len(waves) == 2
    assert {s.step_id for s in waves[0]} == {"fetch_a", "fetch_b"}
    assert [s.step_id for s in waves[1]] == ["combine"]


def test_optimize_plan_handles_purely_sequential_dependencies(planning_service):
    plan = planning_service.build_plan([
        ("step1", "tool-1", {"x": 1}),
        ("step2", "tool-2", {"y": "$steps.step1.out"}),
        ("step3", "tool-3", {"z": "$steps.step2.out"}),
    ])
    waves = planning_service.optimize_plan(plan)
    assert [w[0].step_id for w in waves] == ["step1", "step2", "step3"]
