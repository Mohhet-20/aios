"""Real connector behavior, no mocked business logic — httpx calls use
`httpx.MockTransport` (a real HTTP client stack, just swapping the
network for a scripted response, the same pattern every AIOS project's
provider tests use), and everything else (subprocess sandboxing, file
I/O, SQLite queries, CSV parsing) hits the real thing directly."""
import json

import httpx
import pytest

from tool_platform.connectors.code_execution import PythonExecutionHandler, ShellCommandHandler
from tool_platform.sandbox.subprocess_sandbox import SANDBOX_AVAILABLE
from tool_platform.connectors.database_query import DatabaseQueryHandler
from tool_platform.connectors.document_reader import DocumentReaderHandler
from tool_platform.connectors.embedding_generator import EmbeddingGeneratorHandler
from tool_platform.connectors.file_manager import FileManagerHandler
from tool_platform.connectors.http_client import HttpClientHandler
from tool_platform.connectors.mcp_server import McpServerHandler
from tool_platform.connectors.media_processing import MediaProcessingHandler
from tool_platform.connectors.web_search import WebSearchHandler
from tool_platform.core.exceptions import ToolExecutionError
from tool_platform.models.execution import ToolExecutionModel
from tool_platform.models.tool import ToolModel, ToolVersionModel
from tool_platform.sandbox.network_policy import NetworkPolicy
from tool_platform.tool_execution.context import ToolCallContext


def _ctx(**overrides) -> ToolCallContext:
    defaults = dict(
        tool=ToolModel(id="t1", workspace_id="ws1", organization_id="org1", name="T", slug="t", owner_id="u1", category="custom"),
        tool_version=ToolVersionModel(id="v1", tool_id="t1", version_number=1, created_by="u1"),
        execution=ToolExecutionModel(id="e1", tool_id="t1", tool_version_id="v1", workspace_id="ws1", timeout_seconds=30),
        input_data={}, config={},
    )
    defaults.update(overrides)
    return ToolCallContext(**defaults)


# -- http_client ----------------------------------------------------------------------

@pytest.mark.asyncio
async def test_http_client_get_request():
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.method == "GET"
        return httpx.Response(200, json={"ok": True})

    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    connector = HttpClientHandler(client=client)
    result = await connector.execute(_ctx(config={"url": "https://api.example.com/data", "method": "GET"}))
    assert result["status_code"] == 200
    assert result["body"] == {"ok": True}
    assert result["network_bytes"] > 0
    await client.aclose()


@pytest.mark.asyncio
async def test_http_client_injects_bearer_auth():
    captured = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["auth"] = request.headers.get("authorization")
        return httpx.Response(200, json={})

    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    connector = HttpClientHandler(client=client)
    await connector.execute(_ctx(
        config={"url": "https://api.example.com", "credential_type": "oauth2"},
        credential_secret={"access_token": "tok123"},
    ))
    assert captured["auth"] == "Bearer tok123"
    await client.aclose()


@pytest.mark.asyncio
async def test_http_client_missing_url_raises():
    connector = HttpClientHandler()
    with pytest.raises(ToolExecutionError):
        await connector.execute(_ctx())


@pytest.mark.asyncio
async def test_http_client_respects_network_policy():
    connector = HttpClientHandler()
    policy = NetworkPolicy()  # default deny-all
    with pytest.raises(Exception):
        await connector.execute(_ctx(config={"url": "https://evil.com"}, network_policy=policy))


@pytest.mark.asyncio
async def test_http_client_compensate_calls_compensate_url():
    called = {}

    def handler(request: httpx.Request) -> httpx.Response:
        called["url"] = str(request.url)
        return httpx.Response(200, json={})

    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    connector = HttpClientHandler(client=client)
    await connector.compensate(_ctx(config={"compensate_url": "https://api.example.com/undo"}))
    assert called["url"] == "https://api.example.com/undo"
    await client.aclose()


# -- code execution ---------------------------------------------------------------------

@pytest.mark.skipif(not SANDBOX_AVAILABLE, reason="needs POSIX rlimits (runs on Linux CI)")
@pytest.mark.asyncio
async def test_python_execution_connector_runs_real_code():
    connector = PythonExecutionHandler()
    result = await connector.execute(_ctx(input_data={"code": "print('hi from connector')"}))
    assert "hi from connector" in result["stdout"]


@pytest.mark.skipif(not SANDBOX_AVAILABLE, reason="needs POSIX rlimits (runs on Linux CI)")
@pytest.mark.asyncio
async def test_python_execution_connector_raises_on_failure():
    connector = PythonExecutionHandler()
    with pytest.raises(ToolExecutionError):
        await connector.execute(_ctx(input_data={"code": "import sys; sys.exit(1)"}))


@pytest.mark.skipif(not SANDBOX_AVAILABLE, reason="needs POSIX rlimits (runs on Linux CI)")
@pytest.mark.asyncio
async def test_shell_command_connector_runs_real_command():
    connector = ShellCommandHandler()
    result = await connector.execute(_ctx(input_data={"command": ["echo", "connector shell test"]}))
    assert "connector shell test" in result["stdout"]


# -- file manager -------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_file_manager_write_then_read(tmp_path):
    connector = FileManagerHandler()
    write_ctx = _ctx(config={"base_dir": str(tmp_path)}, input_data={"operation": "write", "path": "note.txt", "content": "hello"})
    await connector.execute(write_ctx)
    read_ctx = _ctx(config={"base_dir": str(tmp_path)}, input_data={"operation": "read", "path": "note.txt"})
    result = await connector.execute(read_ctx)
    assert result["content"] == "hello"


@pytest.mark.asyncio
async def test_file_manager_blocks_path_traversal(tmp_path):
    connector = FileManagerHandler()
    ctx = _ctx(config={"base_dir": str(tmp_path)}, input_data={"operation": "read", "path": "../../etc/passwd"})
    with pytest.raises(ToolExecutionError):
        await connector.execute(ctx)


@pytest.mark.asyncio
async def test_file_manager_list_directory(tmp_path):
    (tmp_path / "a.txt").write_text("a")
    (tmp_path / "b.txt").write_text("b")
    connector = FileManagerHandler()
    result = await connector.execute(_ctx(config={"base_dir": str(tmp_path)}, input_data={"operation": "list", "path": "."}))
    assert result["entries"] == ["a.txt", "b.txt"]


# -- database query -----------------------------------------------------------------------

@pytest.mark.asyncio
async def test_database_query_connector_real_sqlite(tmp_path):
    import aiosqlite
    db_path = str(tmp_path / "test.db")
    async with aiosqlite.connect(db_path) as db:
        await db.execute("CREATE TABLE users (id INTEGER, name TEXT)")
        await db.execute("INSERT INTO users VALUES (1, 'Alice')")
        await db.commit()

    connector = DatabaseQueryHandler()
    result = await connector.execute(_ctx(config={"connection_string": db_path}, input_data={"query": "SELECT * FROM users"}))
    assert result["rows"] == [{"id": 1, "name": "Alice"}]
    assert result["row_count"] == 1


@pytest.mark.asyncio
async def test_database_query_connector_insert(tmp_path):
    import aiosqlite
    db_path = str(tmp_path / "test2.db")
    async with aiosqlite.connect(db_path) as db:
        await db.execute("CREATE TABLE items (id INTEGER)")
        await db.commit()

    connector = DatabaseQueryHandler()
    result = await connector.execute(_ctx(config={"connection_string": db_path}, input_data={"query": "INSERT INTO items VALUES (?)", "params": [42]}))
    assert result["rows_affected"] == 1


# -- web search ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_web_search_ranks_by_term_overlap():
    docs = [
        {"title": "Python docs", "text": "python programming language tutorial"},
        {"title": "Unrelated", "text": "cooking recipes for dinner"},
    ]
    connector = WebSearchHandler(docs)
    result = await connector.execute(_ctx(input_data={"query": "python tutorial"}))
    assert result["results"][0]["title"] == "Python docs"


@pytest.mark.asyncio
async def test_web_search_requires_query():
    connector = WebSearchHandler([])
    with pytest.raises(ToolExecutionError):
        await connector.execute(_ctx())


# -- document reader ----------------------------------------------------------------------

@pytest.mark.asyncio
async def test_document_reader_csv():
    connector = DocumentReaderHandler()
    result = await connector.execute(_ctx(input_data={"format": "csv", "content": "name,age\nAlice,30\nBob,25"}))
    assert result["row_count"] == 2
    assert result["rows"][0] == {"name": "Alice", "age": "30"}


@pytest.mark.asyncio
async def test_document_reader_plain_text():
    connector = DocumentReaderHandler()
    result = await connector.execute(_ctx(input_data={"format": "text", "content": "hello world"}))
    assert result["text"] == "hello world"


@pytest.mark.asyncio
async def test_document_reader_pdf_raises_honest_error():
    connector = DocumentReaderHandler()
    with pytest.raises(ToolExecutionError, match="pypdf"):
        await connector.execute(_ctx(input_data={"format": "pdf", "content": "binary-ish"}))


# -- media processing (honest stub) --------------------------------------------------------

@pytest.mark.asyncio
async def test_media_processing_raises_honest_error():
    connector = MediaProcessingHandler()
    with pytest.raises(ToolExecutionError):
        await connector.execute(_ctx(input_data={"media_type": "image"}))


# -- embedding generator ------------------------------------------------------------------

class _FakeEmbeddingEngine:
    async def embed(self, request):
        class _Response:
            embeddings = [[0.1, 0.2, 0.3]]
            dimensions = 3
            model = request.model or "fake-embed-model"
        return _Response()


class _FakeAiCore:
    embedding_engine = _FakeEmbeddingEngine()


@pytest.mark.asyncio
async def test_embedding_generator_uses_ai_core():
    connector = EmbeddingGeneratorHandler()
    result = await connector.execute(_ctx(input_data={"input": "hello world"}, ai_core=_FakeAiCore()))
    assert result["embeddings"] == [[0.1, 0.2, 0.3]]
    assert result["dimensions"] == 3


@pytest.mark.asyncio
async def test_embedding_generator_requires_ai_core():
    connector = EmbeddingGeneratorHandler()
    with pytest.raises(ToolExecutionError):
        await connector.execute(_ctx(input_data={"input": "x"}))


# -- mcp_server ----------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_mcp_server_calls_json_rpc():
    def handler(request: httpx.Request) -> httpx.Response:
        body = json.loads(request.content)
        assert body["method"] == "list_tools"
        return httpx.Response(200, json={"jsonrpc": "2.0", "id": 1, "result": {"tools": ["a", "b"]}})

    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    connector = McpServerHandler(client=client)
    result = await connector.execute(_ctx(config={"server_url": "https://mcp.example.com"}, input_data={"method": "list_tools"}))
    assert result["result"] == {"tools": ["a", "b"]}
    await client.aclose()


@pytest.mark.asyncio
async def test_mcp_server_error_response_raises():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"jsonrpc": "2.0", "id": 1, "error": {"code": -1, "message": "boom"}})

    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    connector = McpServerHandler(client=client)
    with pytest.raises(ToolExecutionError):
        await connector.execute(_ctx(config={"server_url": "https://mcp.example.com"}, input_data={"method": "x"}))
    await client.aclose()
