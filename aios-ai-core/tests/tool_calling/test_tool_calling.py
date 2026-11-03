import asyncio

import pytest

from ai_core.schemas.tools import ToolCall, ToolDefinition
from ai_core.tool_calling.executor import ToolExecutor
from ai_core.tool_calling.mcp_compat import from_mcp_tool_spec, to_mcp_tool_spec
from ai_core.tool_calling.registry import ToolRegistry
from ai_core.tool_calling.sandbox import ToolSandbox


async def _add(a: int, b: int) -> int:
    return a + b


async def _slow() -> str:
    await asyncio.sleep(5)
    return "done"


async def _boom() -> None:
    raise ValueError("handler exploded")


def _registry() -> ToolRegistry:
    registry = ToolRegistry()
    registry.register(
        ToolDefinition(
            name="add",
            description="add two numbers",
            parameters={"type": "object", "properties": {"a": {"type": "integer"}, "b": {"type": "integer"}}, "required": ["a", "b"]},
        ),
        _add,
    )
    registry.register(
        ToolDefinition(name="slow", description="slow tool", timeout_seconds=0.05, parameters={"type": "object", "properties": {}}),
        _slow,
    )
    registry.register(
        ToolDefinition(name="boom", description="always fails", parameters={"type": "object", "properties": {}}),
        _boom,
    )
    registry.register(
        ToolDefinition(
            name="delete_account", description="dangerous", requires_permission="tool:delete_account",
            parameters={"type": "object", "properties": {}},
        ),
        _add,
    )
    return registry


@pytest.mark.asyncio
async def test_execute_one_success():
    executor = ToolExecutor(_registry())
    result = await executor.execute_one(ToolCall(id="1", name="add", arguments={"a": 2, "b": 3}))
    assert result.content == 5
    assert result.is_error is False


@pytest.mark.asyncio
async def test_execute_one_unknown_tool_returns_error_not_raise():
    executor = ToolExecutor(_registry())
    result = await executor.execute_one(ToolCall(id="1", name="does_not_exist", arguments={}))
    assert result.is_error is True
    assert "no tool registered" in result.error


@pytest.mark.asyncio
async def test_execute_one_invalid_arguments_returns_validation_error():
    executor = ToolExecutor(_registry())
    result = await executor.execute_one(ToolCall(id="1", name="add", arguments={"a": "not-an-int", "b": 3}))
    assert result.is_error is True
    assert "schema validation" in result.error


@pytest.mark.asyncio
async def test_execute_one_missing_permission_denied():
    executor = ToolExecutor(_registry())
    result = await executor.execute_one(ToolCall(id="1", name="delete_account", arguments={}), granted_permissions=set())
    assert result.is_error is True
    assert "permission denied" in result.error


@pytest.mark.asyncio
async def test_execute_one_with_permission_succeeds():
    executor = ToolExecutor(_registry())
    result = await executor.execute_one(
        ToolCall(id="1", name="delete_account", arguments={"a": 1, "b": 1}), granted_permissions={"tool:delete_account"}
    )
    assert result.is_error is False


@pytest.mark.asyncio
async def test_execute_one_timeout_returns_error():
    executor = ToolExecutor(_registry())
    result = await executor.execute_one(ToolCall(id="1", name="slow", arguments={}))
    assert result.is_error is True
    assert "timed out" in result.error


@pytest.mark.asyncio
async def test_execute_one_handler_exception_returns_error_not_raise():
    executor = ToolExecutor(_registry())
    result = await executor.execute_one(ToolCall(id="1", name="boom", arguments={}))
    assert result.is_error is True
    assert "exploded" in result.error


@pytest.mark.asyncio
async def test_execute_parallel_runs_concurrently():
    executor = ToolExecutor(_registry())
    calls = [ToolCall(id=str(i), name="add", arguments={"a": i, "b": 1}) for i in range(5)]
    results = await executor.execute_parallel(calls)
    assert [r.content for r in results] == [1, 2, 3, 4, 5]


@pytest.mark.asyncio
async def test_execute_sequential_preserves_order():
    executor = ToolExecutor(_registry())
    calls = [ToolCall(id=str(i), name="add", arguments={"a": i, "b": 0}) for i in range(3)]
    results = await executor.execute_sequential(calls)
    assert [r.content for r in results] == [0, 1, 2]


@pytest.mark.asyncio
async def test_custom_sandbox_is_used():
    class RecordingSandbox(ToolSandbox):
        def __init__(self):
            self.invocations = 0

        async def run(self, handler, arguments):
            self.invocations += 1
            return await handler(**arguments)

    sandbox = RecordingSandbox()
    executor = ToolExecutor(_registry(), sandbox=sandbox)
    await executor.execute_one(ToolCall(id="1", name="add", arguments={"a": 1, "b": 1}))
    assert sandbox.invocations == 1


def test_mcp_roundtrip():
    definition = ToolDefinition(
        name="search", description="web search", parameters={"type": "object", "properties": {"q": {"type": "string"}}}
    )
    spec = to_mcp_tool_spec(definition)
    assert spec["inputSchema"] == definition.parameters
    rebuilt = from_mcp_tool_spec(spec)
    assert rebuilt.name == "search"
    assert rebuilt.parameters == definition.parameters
