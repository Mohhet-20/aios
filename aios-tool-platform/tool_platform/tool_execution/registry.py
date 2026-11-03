"""ConnectorRegistry: maps a tool version's `connector_key` -> a
`ConnectorHandler` instance. The engine dispatches purely by looking up
`connector_key` in this registry; it never branches on `category` or
any other tool metadata. Adding a new built-in connector, or overriding
one for a specific deployment (e.g. a production `DatabaseQueryHandler`
backed by a real driver), is a dict entry here — not a change to
`engine.py`. `build_default_connector_registry` wires every real,
working reference connector from `connectors/` (Task 107) plus the
always-available `echo`/`custom` fallbacks this module itself owns."""
from __future__ import annotations

from typing import Any

import httpx

from tool_platform.core.exceptions import UnknownToolTypeError
from tool_platform.tool_execution.handlers.base import ConnectorHandler
from tool_platform.tool_execution.handlers.builtin import EchoHandler, FunctionRegistryHandler


class ConnectorRegistry:
    def __init__(self, handlers: dict[str, ConnectorHandler]):
        self._handlers = dict(handlers)

    def get(self, connector_key: str | None) -> ConnectorHandler:
        key = connector_key or "echo"
        handler = self._handlers.get(key)
        if handler is None:
            raise UnknownToolTypeError(f"no connector registered for connector_key '{key}'")
        return handler

    def register(self, connector_key: str, handler: ConnectorHandler) -> None:
        self._handlers[connector_key] = handler


def build_default_connector_registry(
    *, custom_functions: dict[str, Any] | None = None, http_client: httpx.AsyncClient | None = None,
    web_search_documents: list[dict[str, str]] | None = None,
) -> ConnectorRegistry:
    from tool_platform.connectors.code_execution import PythonExecutionHandler, ShellCommandHandler
    from tool_platform.connectors.database_query import DatabaseQueryHandler
    from tool_platform.connectors.document_reader import DocumentReaderHandler
    from tool_platform.connectors.embedding_generator import EmbeddingGeneratorHandler
    from tool_platform.connectors.file_manager import FileManagerHandler
    from tool_platform.connectors.http_client import HttpClientHandler
    from tool_platform.connectors.mcp_server import McpServerHandler
    from tool_platform.connectors.media_processing import MediaProcessingHandler
    from tool_platform.connectors.web_search import WebSearchHandler

    return ConnectorRegistry({
        "echo": EchoHandler(),
        "custom": FunctionRegistryHandler(custom_functions),
        "http_client": HttpClientHandler(client=http_client),
        "python_execution": PythonExecutionHandler(),
        "shell_command": ShellCommandHandler(),
        "file_manager": FileManagerHandler(),
        "database_query": DatabaseQueryHandler(),
        "embedding_generator": EmbeddingGeneratorHandler(),
        "web_search": WebSearchHandler(web_search_documents),
        "document_reader": DocumentReaderHandler(),
        "media_processing": MediaProcessingHandler(),
        "mcp_server": McpServerHandler(client=http_client),
        # github/slack are, mechanically, HTTP calls with connector-specific
        # request shaping (base URL + auth headers baked into a tool
        # version's `configuration`) — they route through the same
        # HttpClientHandler rather than duplicating request/response code.
        "github": HttpClientHandler(client=http_client),
        "slack": HttpClientHandler(client=http_client),
        "notification": HttpClientHandler(client=http_client),
    })
