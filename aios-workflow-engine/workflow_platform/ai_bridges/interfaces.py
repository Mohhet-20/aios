"""Protocol interfaces for cross-platform integration nodes (AGENT,
PROMPT, MEMORY_READ, MEMORY_WRITE, RETRIEVER, KNOWLEDGE_SEARCH,
DOCUMENT_PARSER, FUNCTION_CALL). The Workflow Engine depends only on
these Protocols — never on the Agent/Prompt/Memory/Knowledge/Tool
Platforms directly — the same deliberate boundary the Memory Platform
drew around its own sibling-platform integrations in the memory platform.

Task 87 (Execution Engine) defines these interfaces and wires a minimal,
deterministic in-process reference implementation (`reference_bridges.py`)
so the engine is fully testable end-to-end without any sibling platform
installed. Task 92 (AI Integration bridges) is where a *substantive*
reference implementation — one that actually models what calling into a
real Agent/Prompt/Memory/Knowledge service looks like — replaces this
placeholder; the Protocol shapes defined here are the stable contract
that later implementation swaps in behind."""
from __future__ import annotations

from typing import Any, Protocol, runtime_checkable


@runtime_checkable
class AgentBridge(Protocol):
    async def run_agent(self, agent_id: str, *, task: str, context: dict[str, Any]) -> dict[str, Any]: ...


@runtime_checkable
class PromptBridge(Protocol):
    async def run_prompt(self, prompt_id: str, *, variables: dict[str, Any]) -> dict[str, Any]: ...


@runtime_checkable
class MemoryBridge(Protocol):
    async def read_memory(self, *, scope: str, query: dict[str, Any]) -> dict[str, Any]: ...
    async def write_memory(self, *, scope: str, content: dict[str, Any]) -> dict[str, Any]: ...
    async def undo_write(self, *, scope: str, write_ref: str) -> None: ...
    async def retrieve(self, *, query: str, top_k: int) -> dict[str, Any]: ...


@runtime_checkable
class KnowledgeBridge(Protocol):
    async def search(self, *, query: str, top_k: int = 5) -> dict[str, Any]: ...


@runtime_checkable
class DocumentIntelligenceBridge(Protocol):
    async def parse_document(self, *, file_ref: str, mime_type: str | None = None) -> dict[str, Any]: ...


@runtime_checkable
class ToolBridge(Protocol):
    async def call_function(self, function_name: str, *, arguments: dict[str, Any]) -> dict[str, Any]: ...


class BridgeSet:
    """Bag of bridge implementations the engine passes into node handler
    context. Any bridge left unset causes the corresponding node handler
    to raise a clear `NodeExecutionError` rather than silently no-op-ing."""

    def __init__(
        self,
        *,
        agent: AgentBridge | None = None,
        prompt: PromptBridge | None = None,
        memory: MemoryBridge | None = None,
        knowledge: KnowledgeBridge | None = None,
        document_intelligence: DocumentIntelligenceBridge | None = None,
        tool: ToolBridge | None = None,
    ):
        self.agent = agent
        self.prompt = prompt
        self.memory = memory
        self.knowledge = knowledge
        self.document_intelligence = document_intelligence
        self.tool = tool
