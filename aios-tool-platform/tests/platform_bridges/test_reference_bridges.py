import pytest

from tool_platform.core.exceptions import ToolPlanningError
from tool_platform.platform_bridges.interfaces import PlatformBridgeSet
from tool_platform.platform_bridges.reference_bridges import (
    InProcessAgentBridge,
    InProcessMemoryBridge,
    InProcessPromptBridge,
    InProcessWorkflowBridge,
    build_reference_bridge_set,
)


@pytest.mark.asyncio
async def test_workflow_bridge_raises_for_unregistered_workflow():
    bridge = InProcessWorkflowBridge()
    with pytest.raises(ToolPlanningError):
        await bridge.trigger_workflow("wf-1", input_variables={})


@pytest.mark.asyncio
async def test_workflow_bridge_invokes_registered_callback():
    bridge = InProcessWorkflowBridge()
    calls = []

    async def callback(*, input_variables):
        calls.append(input_variables)
        return {"status": "started", "run_id": "run-1"}

    bridge.register("wf-1", callback)
    result = await bridge.trigger_workflow("wf-1", input_variables={"x": 1})
    assert result == {"status": "started", "run_id": "run-1"}
    assert calls == [{"x": 1}]


@pytest.mark.asyncio
async def test_agent_bridge_raises_for_unregistered_agent():
    bridge = InProcessAgentBridge()
    with pytest.raises(ToolPlanningError):
        await bridge.notify_agent("agent-1", message="hi", context={})


@pytest.mark.asyncio
async def test_agent_bridge_invokes_registered_callback():
    bridge = InProcessAgentBridge()
    received = {}

    async def callback(*, message, context):
        received["message"] = message
        received["context"] = context

    bridge.register("agent-1", callback)
    await bridge.notify_agent("agent-1", message="hello", context={"k": "v"})
    assert received == {"message": "hello", "context": {"k": "v"}}


@pytest.mark.asyncio
async def test_memory_bridge_writes_and_reads_scoped_results():
    bridge = InProcessMemoryBridge()
    assert await bridge.read_results("scope-a") == []

    result = await bridge.write_result("scope-a", {"foo": "bar"})
    assert result["stored"] is True
    assert result["count"] == 1

    await bridge.write_result("scope-a", {"foo": "baz"})
    results = await bridge.read_results("scope-a")
    assert results == [{"foo": "bar"}, {"foo": "baz"}]

    # a different scope is isolated
    assert await bridge.read_results("scope-b") == []


@pytest.mark.asyncio
async def test_prompt_bridge_renders_registered_template():
    bridge = InProcessPromptBridge({"greet": "Hello {{name}}, welcome to {{place}}!"})
    rendered = await bridge.render_prompt("greet", {"name": "Ada", "place": "AIOS"})
    assert rendered == "Hello Ada, welcome to AIOS!"


@pytest.mark.asyncio
async def test_prompt_bridge_leaves_unresolved_variables_untouched():
    bridge = InProcessPromptBridge({"greet": "Hello {{name}}!"})
    rendered = await bridge.render_prompt("greet", {})
    assert rendered == "Hello {{name}}!"


@pytest.mark.asyncio
async def test_prompt_bridge_raises_for_unregistered_prompt():
    bridge = InProcessPromptBridge()
    with pytest.raises(ToolPlanningError):
        await bridge.render_prompt("missing", {})


@pytest.mark.asyncio
async def test_prompt_bridge_register_template_after_construction():
    bridge = InProcessPromptBridge()
    bridge.register_template("later", "Value: {{v}}")
    assert await bridge.render_prompt("later", {"v": "42"}) == "Value: 42"


def test_build_reference_bridge_set_wires_all_four_bridges():
    bridge_set = build_reference_bridge_set(templates={"p": "hi {{n}}"})
    assert isinstance(bridge_set, PlatformBridgeSet)
    assert isinstance(bridge_set.workflow, InProcessWorkflowBridge)
    assert isinstance(bridge_set.agent, InProcessAgentBridge)
    assert isinstance(bridge_set.memory, InProcessMemoryBridge)
    assert isinstance(bridge_set.prompt, InProcessPromptBridge)


@pytest.mark.asyncio
async def test_build_reference_bridge_set_prompt_templates_are_usable():
    bridge_set = build_reference_bridge_set(templates={"p": "hi {{n}}"})
    rendered = await bridge_set.prompt.render_prompt("p", {"n": "Bob"})
    assert rendered == "hi Bob"
