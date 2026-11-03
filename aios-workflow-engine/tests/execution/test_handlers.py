"""Direct, isolated tests for the node handlers not already exercised
end-to-end through a full graph in `test_execution_engine.py` — the
bridge-backed AI nodes, the real-HTTP integration nodes (via
`httpx.MockTransport`, so no network access), and the data/utility
nodes."""
import httpx
import pytest

from workflow_platform.ai_bridges.reference_bridges import build_reference_bridge_set
from workflow_platform.core.exceptions import NodeExecutionError, ValidationError
from workflow_platform.workflow_engine.context import NodeContext
from workflow_platform.workflow_engine.handlers.ai_nodes import (
    AgentHandler,
    DocumentParserHandler,
    EmbeddingGeneratorHandler,
    FunctionCallHandler,
    KnowledgeSearchHandler,
    MemoryReadHandler,
    MemoryWriteHandler,
    PromptHandler,
    RetrieverHandler,
)
from workflow_platform.workflow_engine.handlers.data import (
    DatabaseQueryHandler,
    FileProcessingHandler,
    FileUploadHandler,
    PythonExecutionHandler,
)
from workflow_platform.workflow_engine.handlers.integration import RestApiHandler, WebhookHandler


def _ctx(node_type: str, *, config=None, variables=None, bridges=None, extra=None, execution=None, node=None, node_execution=None):
    return NodeContext(
        execution=execution, node=node, node_execution=node_execution, node_definition=None,
        config=config or {}, variables=variables if variables is not None else {}, ai_core=None,
        bridges=bridges or build_reference_bridge_set(), extra=extra or {},
    )


@pytest.mark.asyncio
async def test_agent_handler_calls_bridge_and_formats_task():
    handler = AgentHandler()
    ctx = _ctx("agent", config={"agent_id": "agent-1", "task": "summarize {topic}"}, variables={"topic": "Q3 earnings"})
    result = await handler.execute(ctx)
    assert result["agent_id"] == "agent-1"
    assert "Q3 earnings" in result["task"]


@pytest.mark.asyncio
async def test_agent_handler_requires_bridge():
    handler = AgentHandler()
    ctx = _ctx("agent", config={"agent_id": "a"}, bridges=build_reference_bridge_set())
    ctx.bridges.agent = None
    with pytest.raises(NodeExecutionError):
        await handler.execute(ctx)


@pytest.mark.asyncio
async def test_prompt_handler_merges_variables():
    handler = PromptHandler()
    ctx = _ctx("prompt", config={"prompt_id": "p1", "variables": {"a": 1}}, variables={"b": 2})
    result = await handler.execute(ctx)
    assert result["prompt_id"] == "p1"


@pytest.mark.asyncio
async def test_memory_write_then_read_roundtrip():
    bridges = build_reference_bridge_set()
    write_handler = MemoryWriteHandler()
    ctx = _ctx("memory_write", config={"scope": "wf", "content": {"k": "v"}}, bridges=bridges)
    result = await write_handler.execute(ctx)
    assert "write_ref" in result

    read_handler = MemoryReadHandler()
    read_ctx = _ctx("memory_read", config={"scope": "wf", "query": {}}, bridges=bridges)
    read_result = await read_handler.execute(read_ctx)
    assert read_result["results"] == [{"k": "v"}]


@pytest.mark.asyncio
async def test_retriever_and_knowledge_search_handlers():
    bridges = build_reference_bridge_set()
    retriever_result = await RetrieverHandler().execute(_ctx("retriever", config={"query": "find X", "top_k": 3}, bridges=bridges))
    assert retriever_result["query"] == "find X"

    knowledge_result = await KnowledgeSearchHandler().execute(_ctx("knowledge_search", config={"query": "docs"}, bridges=bridges))
    assert knowledge_result["query"] == "docs"


@pytest.mark.asyncio
async def test_document_parser_handler():
    result = await DocumentParserHandler().execute(_ctx("document_parser", config={"file_ref": "s3://f.pdf"}))
    assert result["file_ref"] == "s3://f.pdf"


@pytest.mark.asyncio
async def test_function_call_handler():
    result = await FunctionCallHandler().execute(_ctx("function_call", config={"function_name": "add", "arguments": {"a": 2, "b": 3}}))
    assert result["function_name"] == "add"
    assert result["arguments"] == {"a": 2, "b": 3}
    assert result["result"] == 5


@pytest.mark.asyncio
async def test_function_call_handler_unregistered_function_raises():
    with pytest.raises(NodeExecutionError):
        await FunctionCallHandler().execute(_ctx("function_call", config={"function_name": "lookup", "arguments": {"id": 1}}))


@pytest.mark.asyncio
async def test_embedding_generator_handler_uses_ai_core(scripted_ai_core):
    from tests.conftest import make_embedding_response

    ai_core, provider = scripted_ai_core
    provider.push(make_embedding_response([[0.1, 0.2, 0.3]]))
    ctx = _ctx("embedding_generator", config={"input": "hello world"})
    ctx.ai_core = ai_core
    result = await EmbeddingGeneratorHandler().execute(ctx)
    assert result["dimensions"] == 3


def _mock_client(handler_fn) -> httpx.AsyncClient:
    return httpx.AsyncClient(transport=httpx.MockTransport(handler_fn))


@pytest.mark.asyncio
async def test_rest_api_handler_real_http_call_via_mock_transport():
    def responder(request: httpx.Request) -> httpx.Response:
        assert request.method == "POST"
        return httpx.Response(200, json={"ok": True})

    client = _mock_client(responder)
    handler = RestApiHandler(client=client)
    ctx = _ctx("rest_api", config={"method": "POST", "url": "https://example.com/api", "body": {"x": 1}})
    result = await handler.execute(ctx)
    assert result["status_code"] == 200
    assert result["body"] == {"ok": True}
    await client.aclose()


@pytest.mark.asyncio
async def test_rest_api_handler_missing_url_raises():
    handler = RestApiHandler()
    with pytest.raises(NodeExecutionError):
        await handler.execute(_ctx("rest_api", config={"method": "GET"}))


@pytest.mark.asyncio
async def test_rest_api_handler_compensation_calls_compensate_url():
    calls = []

    def responder(request: httpx.Request) -> httpx.Response:
        calls.append(str(request.url))
        return httpx.Response(200, json={})

    client = _mock_client(responder)
    handler = RestApiHandler(client=client)
    ctx = _ctx("rest_api", config={"method": "POST", "url": "https://example.com/charge", "compensate_url": "https://example.com/refund"})
    await handler.compensate(ctx)
    assert calls == ["https://example.com/refund"]
    await client.aclose()


@pytest.mark.asyncio
async def test_webhook_handler_delivers_payload():
    received = {}

    def responder(request: httpx.Request) -> httpx.Response:
        received["body"] = request.content
        return httpx.Response(204)

    client = _mock_client(responder)
    handler = WebhookHandler(client=client)
    ctx = _ctx("webhook", config={"url": "https://hooks.example.com/x", "payload": {"a": 1}})
    result = await handler.execute(ctx)
    assert result["delivered"] is True
    await client.aclose()


@pytest.mark.asyncio
async def test_database_query_handler_uses_injected_executor():
    async def executor(query, params):
        assert query == "SELECT * FROM t WHERE id = :id"
        assert params == {"id": 7}
        return [{"id": 7}]

    handler = DatabaseQueryHandler()
    ctx = _ctx("database_query", config={"query": "SELECT * FROM t WHERE id = :id", "params": {"id": 7}}, extra={"query_executor": executor})
    result = await handler.execute(ctx)
    assert result["row_count"] == 1


@pytest.mark.asyncio
async def test_database_query_handler_without_executor_raises():
    handler = DatabaseQueryHandler()
    with pytest.raises(NodeExecutionError):
        await handler.execute(_ctx("database_query", config={"query": "SELECT 1"}))


@pytest.mark.asyncio
async def test_python_execution_handler_evaluates_safe_expression():
    handler = PythonExecutionHandler()
    ctx = _ctx("python_execution", config={"expression": "a + b", "output_variable": "sum"}, variables={"a": 2, "b": 3})
    result = await handler.execute(ctx)
    assert result["sum"] == 5


@pytest.mark.asyncio
async def test_python_execution_handler_blocks_unsafe_expression():
    handler = PythonExecutionHandler()
    ctx = _ctx("python_execution", config={"expression": "__import__('os')"})
    with pytest.raises(ValidationError):
        await handler.execute(ctx)


@pytest.mark.asyncio
async def test_file_upload_and_processing_handlers():
    upload_result = await FileUploadHandler().execute(_ctx("file_upload", config={"file_ref": "file://a.csv"}))
    assert upload_result["file_ref"] == "file://a.csv"

    processing_result = await FileProcessingHandler().execute(
        _ctx("file_processing", config={"file_ref": "file://a.csv", "operation": "validate"})
    )
    assert processing_result["operation"] == "validate"
    assert processing_result["processed"] is True


@pytest.mark.asyncio
async def test_file_upload_handler_requires_file_ref():
    with pytest.raises(NodeExecutionError):
        await FileUploadHandler().execute(_ctx("file_upload", config={}))
