import pytest
from pydantic import BaseModel

from ai_core.execution.execution_engine import ExecutionEngine
from ai_core.registry.model_metadata import ModelMetadata
from ai_core.registry.model_registry import ModelRegistry
from ai_core.router.model_router import ModelRouter
from ai_core.router.policy import RoutingPolicy
from ai_core.schemas.enums import Role
from ai_core.schemas.messages import ChatMessage
from ai_core.schemas.requests import GenerationRequest
from ai_core.structured_output.engine import StructuredOutputEngine
from ai_core.structured_output.parser import parse_json_response
from ai_core.structured_output.schema_utils import response_format_for_model
from ai_core.utils.exceptions import StructuredOutputError

from tests.execution.conftest import ScriptedProvider, make_response


class Person(BaseModel):
    name: str
    age: int


def test_parse_json_response_handles_markdown_fence():
    raw = '```json\n{"name": "Ada", "age": 30}\n```'
    assert parse_json_response(raw) == {"name": "Ada", "age": 30}


def test_parse_json_response_handles_plain_json():
    assert parse_json_response('{"a": 1}') == {"a": 1}


def test_parse_json_response_extracts_json_amid_prose():
    raw = 'Sure, here you go: {"name": "Bo", "age": 5} Hope that helps!'
    assert parse_json_response(raw) == {"name": "Bo", "age": 5}


def test_parse_json_response_raises_on_garbage():
    with pytest.raises(StructuredOutputError):
        parse_json_response("not json at all")


def test_response_format_for_model_includes_schema_name():
    fmt = response_format_for_model(Person)
    assert fmt["type"] == "json_schema"
    assert fmt["json_schema"]["name"] == "Person"
    assert "age" in fmt["json_schema"]["schema"]["properties"]


def _req():
    return GenerationRequest(messages=[ChatMessage(role=Role.USER, content="describe a person")])


def _engine_with_responses(contents: list[str]):
    from ai_core.schemas.enums import Capability

    registry = ModelRegistry()
    registry.register(ModelMetadata(provider="test", name="m1", priority=1, capabilities={Capability.JSON_OUTPUT}))
    responses = [make_response(f"r{i}", "test", "m1", content=c) for i, c in enumerate(contents)]
    provider = ScriptedProvider("test", responses)
    router = ModelRouter(registry, policy=RoutingPolicy(name="t", strategies=[], max_candidates=1))
    return ExecutionEngine(registry=registry, router=router, providers={"test": provider}), provider


@pytest.mark.asyncio
async def test_structured_output_succeeds_first_try():
    engine, provider = _engine_with_responses(['{"name": "Ada", "age": 30}'])
    so_engine = StructuredOutputEngine(engine)
    result = await so_engine.execute(_req(), Person)
    assert result.instance.name == "Ada"
    assert result.attempts == 1
    assert result.confidence == 1.0
    assert provider.calls == 1


@pytest.mark.asyncio
async def test_structured_output_repairs_after_invalid_json():
    engine, provider = _engine_with_responses(["not valid json", '{"name": "Ada", "age": 30}'])
    so_engine = StructuredOutputEngine(engine, max_repair_attempts=2)
    result = await so_engine.execute(_req(), Person)
    assert result.instance.name == "Ada"
    assert result.attempts == 2
    assert result.confidence == 0.7
    assert provider.calls == 2


@pytest.mark.asyncio
async def test_structured_output_repairs_after_schema_mismatch():
    engine, provider = _engine_with_responses(['{"name": "Ada"}', '{"name": "Ada", "age": 30}'])
    so_engine = StructuredOutputEngine(engine, max_repair_attempts=2)
    result = await so_engine.execute(_req(), Person)
    assert result.attempts == 2
    assert result.instance.age == 30


@pytest.mark.asyncio
async def test_structured_output_gives_up_after_max_repairs():
    engine, provider = _engine_with_responses(["bad", "still bad", "still bad again"])
    so_engine = StructuredOutputEngine(engine, max_repair_attempts=2)
    with pytest.raises(StructuredOutputError):
        await so_engine.execute(_req(), Person)
    assert provider.calls == 3
