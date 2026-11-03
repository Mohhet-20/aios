"""HandlerRegistry: maps `NodeType` -> `NodeHandler` instance. Building
one from `build_default_handler_registry` wires every built-in node type
to a real handler — swapping in a different implementation for one node
type (e.g. a production `DatabaseQueryHandler` backed by a real driver)
is a one-line override on the returned dict, not a fork of this module."""
from __future__ import annotations

from typing import Any

import httpx

from workflow_platform.ai_bridges.interfaces import BridgeSet
from workflow_platform.core.exceptions import UnknownNodeTypeError
from workflow_platform.domain.enums import NodeType
from workflow_platform.workflow_engine.handlers.ai_nodes import (
    AgentHandler,
    DocumentParserHandler,
    EmbeddingGeneratorHandler,
    FunctionCallHandler,
    KnowledgeSearchHandler,
    LlmCallHandler,
    MemoryReadHandler,
    MemoryWriteHandler,
    PromptHandler,
    RetrieverHandler,
)
from workflow_platform.workflow_engine.handlers.base import NodeHandler
from workflow_platform.workflow_engine.handlers.control import (
    ConditionHandler,
    DecisionHandler,
    DelayHandler,
    EndHandler,
    ErrorHandlerHandler,
    LoopHandler,
    MergeHandler,
    ParallelBranchHandler,
    RetryHandler,
    StartHandler,
    WaitHandler,
)
from workflow_platform.workflow_engine.handlers.custom import CustomHandler
from workflow_platform.workflow_engine.handlers.data import (
    DatabaseQueryHandler,
    FileProcessingHandler,
    FileUploadHandler,
    PythonExecutionHandler,
)
from workflow_platform.workflow_engine.handlers.human import ApprovalHandler, NotificationHandler
from workflow_platform.workflow_engine.handlers.integration import RestApiHandler, WebhookHandler


class HandlerRegistry:
    def __init__(self, handlers: dict[str, NodeHandler]):
        self._handlers = dict(handlers)

    def get(self, node_type: str) -> NodeHandler:
        handler = self._handlers.get(node_type)
        if handler is None:
            raise UnknownNodeTypeError(f"no handler registered for node type '{node_type}'")
        return handler

    def register(self, node_type: str, handler: NodeHandler) -> None:
        self._handlers[node_type] = handler


def build_default_handler_registry(
    *, bridges: BridgeSet | None = None, http_client: httpx.AsyncClient | None = None,
    custom_handlers: dict[str, Any] | None = None,
) -> HandlerRegistry:
    bridges = bridges or BridgeSet()
    return HandlerRegistry({
        NodeType.START.value: StartHandler(),
        NodeType.END.value: EndHandler(),
        NodeType.AGENT.value: AgentHandler(),
        NodeType.PROMPT.value: PromptHandler(),
        NodeType.MEMORY_READ.value: MemoryReadHandler(),
        NodeType.MEMORY_WRITE.value: MemoryWriteHandler(),
        NodeType.RETRIEVER.value: RetrieverHandler(),
        NodeType.KNOWLEDGE_SEARCH.value: KnowledgeSearchHandler(),
        NodeType.DECISION.value: DecisionHandler(),
        NodeType.CONDITION.value: ConditionHandler(),
        NodeType.LOOP.value: LoopHandler(),
        NodeType.PARALLEL_BRANCH.value: ParallelBranchHandler(),
        NodeType.MERGE.value: MergeHandler(),
        NodeType.DELAY.value: DelayHandler(),
        NodeType.WAIT.value: WaitHandler(),
        NodeType.APPROVAL.value: ApprovalHandler(),
        NodeType.NOTIFICATION.value: NotificationHandler(),
        NodeType.WEBHOOK.value: WebhookHandler(client=http_client),
        NodeType.REST_API.value: RestApiHandler(client=http_client),
        NodeType.DATABASE_QUERY.value: DatabaseQueryHandler(),
        NodeType.PYTHON_EXECUTION.value: PythonExecutionHandler(),
        NodeType.FILE_UPLOAD.value: FileUploadHandler(),
        NodeType.FILE_PROCESSING.value: FileProcessingHandler(),
        NodeType.DOCUMENT_PARSER.value: DocumentParserHandler(),
        NodeType.EMBEDDING_GENERATOR.value: EmbeddingGeneratorHandler(),
        NodeType.LLM_CALL.value: LlmCallHandler(),
        NodeType.FUNCTION_CALL.value: FunctionCallHandler(),
        NodeType.ERROR_HANDLER.value: ErrorHandlerHandler(),
        NodeType.RETRY.value: RetryHandler(),
        NodeType.CUSTOM.value: CustomHandler(registry=custom_handlers),
    })
