import pytest

from ai_core.execution.execution_engine import ExecutionEngine
from ai_core.prompts.chain import PromptChain, PromptStep
from ai_core.prompts.composer import compose, render_messages
from ai_core.prompts.executor import PromptExecutor
from ai_core.prompts.registry import PromptRegistry
from ai_core.prompts.template import PromptTemplate
from ai_core.registry.model_metadata import ModelMetadata
from ai_core.registry.model_registry import ModelRegistry
from ai_core.router.model_router import ModelRouter
from ai_core.router.policy import RoutingPolicy
from ai_core.schemas.enums import Role
from ai_core.utils.exceptions import PromptValidationError

from tests.execution.conftest import ScriptedProvider, make_response


def test_template_render_substitutes_variables():
    tpl = PromptTemplate(name="greet", role=Role.USER, template="Hello {{name}}, welcome to {{place}}.")
    assert tpl.render({"name": "Ada", "place": "AIOS"}) == "Hello Ada, welcome to AIOS."


def test_template_render_raises_on_missing_variable():
    tpl = PromptTemplate(name="greet", role=Role.USER, template="Hello {{name}}.")
    with pytest.raises(PromptValidationError):
        tpl.render({})


def test_template_auto_extracts_required_variables():
    tpl = PromptTemplate(name="t", role=Role.SYSTEM, template="{{a}} and {{b}}")
    assert tpl.required_variables == {"a", "b"}


def test_render_messages_composes_in_order():
    templates = [
        PromptTemplate(name="sys", role=Role.SYSTEM, template="You are {{persona}}."),
        PromptTemplate(name="user", role=Role.USER, template="{{question}}"),
    ]
    messages = render_messages(templates, {"persona": "helpful", "question": "2+2?"})
    assert [m.role for m in messages] == [Role.SYSTEM, Role.USER]
    assert messages[0].text() == "You are helpful."


def test_compose_builds_system_examples_and_user_turn():
    messages = compose(
        system="Be terse.",
        examples=[("1+1?", "2")],
        user=PromptTemplate(name="q", role=Role.USER, template="{{q}}"),
        variables={"q": "3+3?"},
    )
    assert [m.role for m in messages] == [Role.SYSTEM, Role.USER, Role.ASSISTANT, Role.USER]
    assert messages[-1].text() == "3+3?"


def test_prompt_registry_versions_increment_and_fetch():
    registry = PromptRegistry()
    registry.register("greeting", Role.USER, "Hi {{name}}")
    registry.register("greeting", Role.USER, "Hello there {{name}}")
    latest = registry.get_latest("greeting")
    assert latest.version == 2
    assert registry.get_version("greeting", 1).version == 1
    assert len(registry.list_versions("greeting")) == 2


@pytest.mark.asyncio
async def test_prompt_executor_renders_and_executes():
    registry = ModelRegistry()
    registry.register(ModelMetadata(provider="test", name="m1", priority=1))
    provider = ScriptedProvider("test", [make_response("r1", "test", "m1", content="Ahoy!")])
    router = ModelRouter(registry, policy=RoutingPolicy(name="t", strategies=[], max_candidates=1))
    engine = ExecutionEngine(registry=registry, router=router, providers={"test": provider})
    executor = PromptExecutor(engine)

    tpl = PromptTemplate(name="greet", role=Role.USER, template="Say hi to {{name}}")
    resp = await executor.execute([tpl], {"name": "Ada"}, postprocess=str.upper)
    assert resp.content == "AHOY!"


@pytest.mark.asyncio
async def test_prompt_chain_threads_previous_output_into_next_step():
    registry = ModelRegistry()
    registry.register(ModelMetadata(provider="test", name="m1", priority=1))
    provider = ScriptedProvider(
        "test",
        [make_response("r1", "test", "m1", content="draft text"), make_response("r2", "test", "m1", content="polished text")],
    )
    router = ModelRouter(registry, policy=RoutingPolicy(name="t", strategies=[], max_candidates=1))
    engine = ExecutionEngine(registry=registry, router=router, providers={"test": provider})
    executor = PromptExecutor(engine)

    draft_tpl = PromptTemplate(name="draft", role=Role.USER, template="Write about {{topic}}")
    polish_tpl = PromptTemplate(name="polish", role=Role.USER, template="Polish this: {{previous_output}}")

    chain = PromptChain(
        steps=[
            PromptStep(templates=[draft_tpl], variable_mapper=lambda state, prev: {"topic": state["topic"]}),
            PromptStep(templates=[polish_tpl], variable_mapper=lambda state, prev: {"previous_output": prev.content}),
        ],
        executor=executor,
    )
    responses = await chain.run({"topic": "AI"})
    assert responses[0].content == "draft text"
    assert responses[1].content == "polished text"
