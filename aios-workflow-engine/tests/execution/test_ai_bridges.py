"""Task 92: the working in-process reference bridge implementations —
real lexical retrieval ranking, real prompt templating (with and without
a live AI Core), a real AI-Core-backed agent bridge, real text chunking
(and explicit rejection of non-text input), and the extensible function
registry."""
import pytest

from workflow_platform.ai_bridges.reference_bridges import (
    AICoreAgentBridge,
    FunctionRegistryToolBridge,
    InProcessKnowledgeBridge,
    InProcessMemoryBridge,
    LexicalIndex,
    TemplatePromptBridge,
    TextDocumentIntelligenceBridge,
    build_reference_bridge_set,
)
from workflow_platform.core.exceptions import NodeExecutionError


def test_lexical_index_scores_term_overlap():
    assert LexicalIndex.score("quarterly earnings report", "the quarterly earnings report is ready") > 0
    assert LexicalIndex.score("quarterly earnings", "totally unrelated text") == 0
    assert LexicalIndex.score("", "anything") == 0


@pytest.mark.asyncio
async def test_memory_bridge_retrieve_ranks_by_relevance():
    bridge = InProcessMemoryBridge()
    await bridge.write_memory(scope="wf", content={"text": "the cat sat on the mat"})
    await bridge.write_memory(scope="wf", content={"text": "quarterly earnings beat expectations"})
    await bridge.write_memory(scope="wf", content={"text": "earnings call transcript for Q3"})

    result = await bridge.retrieve(query="quarterly earnings", top_k=2)
    assert len(result["results"]) == 2
    texts = [r["text"] for r in result["results"]]
    assert "quarterly earnings beat expectations" in texts
    assert "the cat sat on the mat" not in texts


@pytest.mark.asyncio
async def test_memory_bridge_retrieve_excludes_zero_relevance_items():
    bridge = InProcessMemoryBridge()
    await bridge.write_memory(scope="wf", content={"text": "totally unrelated content"})
    result = await bridge.retrieve(query="quarterly earnings", top_k=5)
    assert result["results"] == []


@pytest.mark.asyncio
async def test_knowledge_bridge_search_ranks_documents():
    bridge = InProcessKnowledgeBridge()
    bridge.index_document("Onboarding Guide", "how to onboard a new employee at the company")
    bridge.index_document("Earnings FAQ", "frequently asked questions about quarterly earnings")

    result = await bridge.search(query="earnings", top_k=1)
    assert len(result["results"]) == 1
    assert result["results"][0]["title"] == "Earnings FAQ"


@pytest.mark.asyncio
async def test_prompt_bridge_renders_registered_template():
    bridge = TemplatePromptBridge()
    bridge.register_template("greeting", "Hello {name}, welcome to {product}!")
    result = await bridge.run_prompt("greeting", variables={"name": "Mohhet", "product": "AIOS"})
    assert result["output"] == "Hello Mohhet, welcome to AIOS!"


@pytest.mark.asyncio
async def test_prompt_bridge_missing_variable_raises_clear_error():
    bridge = TemplatePromptBridge()
    bridge.register_template("greeting", "Hello {name}!")
    with pytest.raises(NodeExecutionError):
        await bridge.run_prompt("greeting", variables={})


@pytest.mark.asyncio
async def test_prompt_bridge_unregistered_id_does_not_raise():
    bridge = TemplatePromptBridge()
    result = await bridge.run_prompt("nonexistent", variables={"a": 1})
    assert result["prompt_id"] == "nonexistent"


@pytest.mark.asyncio
async def test_prompt_bridge_calls_ai_core_when_provided(scripted_ai_core):
    from tests.conftest import make_response

    ai_core, provider = scripted_ai_core
    provider.push(make_response("Rendered and generated response"))

    bridge = TemplatePromptBridge(ai_core=ai_core)
    bridge.register_template("p1", "Summarize: {topic}")
    result = await bridge.run_prompt("p1", variables={"topic": "Q3 results"})
    assert result["rendered"] == "Summarize: Q3 results"
    assert result["output"] == "Rendered and generated response"
    assert provider.calls == 1


@pytest.mark.asyncio
async def test_agent_bridge_calls_ai_core(scripted_ai_core):
    from tests.conftest import make_response

    ai_core, provider = scripted_ai_core
    provider.push(make_response("Task completed successfully"))

    bridge = AICoreAgentBridge(ai_core)
    result = await bridge.run_agent("researcher-1", task="find the latest revenue figure", context={"company": "Acme"})
    assert result["agent_id"] == "researcher-1"
    assert result["result"] == "Task completed successfully"
    assert provider.calls == 1


@pytest.mark.asyncio
async def test_document_intelligence_bridge_chunks_text():
    bridge = TextDocumentIntelligenceBridge(chunk_size_words=3)
    result = await bridge.parse_document(file_ref="one two three four five six seven")
    assert result["total_words"] == 7
    assert len(result["chunks"]) == 3
    assert result["chunks"][0]["text"] == "one two three"
    assert result["chunks"][-1]["word_count"] == 1


@pytest.mark.asyncio
async def test_document_intelligence_bridge_rejects_non_text_input():
    bridge = TextDocumentIntelligenceBridge()
    with pytest.raises(NodeExecutionError):
        await bridge.parse_document(file_ref="")


@pytest.mark.asyncio
async def test_tool_bridge_registry_supports_custom_functions():
    bridge = FunctionRegistryToolBridge()
    bridge.register("shout", lambda text: text.upper() + "!!!")
    result = await bridge.call_function("shout", arguments={"text": "hello"})
    assert result["result"] == "HELLO!!!"


@pytest.mark.asyncio
async def test_tool_bridge_bad_arguments_raises_clear_error():
    bridge = FunctionRegistryToolBridge()
    with pytest.raises(NodeExecutionError):
        await bridge.call_function("add", arguments={"a": 1})  # missing 'b'


@pytest.mark.asyncio
async def test_build_reference_bridge_set_wires_ai_core_agent_when_provided(scripted_ai_core):
    ai_core, _provider = scripted_ai_core
    bridges = build_reference_bridge_set(ai_core=ai_core)
    assert isinstance(bridges.agent, AICoreAgentBridge)


@pytest.mark.asyncio
async def test_build_reference_bridge_set_falls_back_to_echo_agent_without_ai_core():
    bridges = build_reference_bridge_set()
    result = await bridges.agent.run_agent("a1", task="do it", context={})
    assert result["agent_id"] == "a1"
