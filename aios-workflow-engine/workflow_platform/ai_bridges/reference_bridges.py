"""Task 92 — working in-process reference implementations of every
bridge Protocol declared in `interfaces.py`. These do real work: an
AgentBridge that actually drives an LLM generation through AI Core when
one is available, a Memory/Knowledge bridge pair sharing a real (if
simple) lexical-overlap relevance ranker instead of returning stored
items in insertion order, a PromptBridge that does real `str.format`
templating (optionally followed by a real LLM call), a DocumentIntel-
ligence bridge that really chunks text content it's handed, and a Tool
bridge backed by a real, extensible function registry rather than an
unconditional echo.

None of these are meant to be the last word on what a production Agent/
Prompt/Memory/Knowledge/Tool Platform integration looks like — that's
the entire point of the Protocol boundary in `interfaces.py`: a real
sibling platform, once wired in as an actual dependency, drops in behind
these same interfaces without the Execution Engine or any node handler
changing a line. Binary document formats (PDF/DOCX/PPTX/XLSX) are
deliberately NOT parsed here — that's the Memory Platform's real
Document Intelligence pipeline's job (see the memory platform's `document_
intelligence/` module); `TextDocumentIntelligenceBridge` only handles
plain-text content handed to it directly."""
from __future__ import annotations

import uuid
from typing import Any, Awaitable, Callable

from workflow_platform.core.exceptions import NodeExecutionError


class LexicalIndex:
    """Shared term-overlap relevance scorer for the Memory and Knowledge
    reference bridges — real, deterministic ranking without pulling in a
    vector index dependency this platform doesn't own. A production
    Memory/Knowledge Platform bridge swaps this for genuine embedding
    similarity (see the Vector Platform built in the memory platform) behind the
    exact same Protocol methods."""

    @staticmethod
    def score(query: str, text: str) -> float:
        q_terms = set(query.lower().split())
        t_terms = set(text.lower().split())
        if not q_terms or not t_terms:
            return 0.0
        return len(q_terms & t_terms) / len(q_terms)


class InProcessMemoryBridge:
    """Real read/write/retrieve semantics over an in-memory store —
    `retrieve()` ranks by actual lexical overlap against each stored
    item's `text` field (or its string form if untyped) rather than
    returning insertion order."""

    def __init__(self) -> None:
        self._store: dict[str, dict[str, dict[str, Any]]] = {}

    async def read_memory(self, *, scope: str, query: dict[str, Any]) -> dict[str, Any]:
        return {"scope": scope, "query": query, "results": list(self._store.get(scope, {}).values())}

    async def write_memory(self, *, scope: str, content: dict[str, Any]) -> dict[str, Any]:
        write_ref = uuid.uuid4().hex
        self._store.setdefault(scope, {})[write_ref] = content
        return {"write_ref": write_ref, "scope": scope}

    async def undo_write(self, *, scope: str, write_ref: str) -> None:
        self._store.get(scope, {}).pop(write_ref, None)

    async def retrieve(self, *, query: str, top_k: int) -> dict[str, Any]:
        scored: list[tuple[float, dict]] = []
        for bucket in self._store.values():
            for item in bucket.values():
                text = str(item.get("text", item)) if isinstance(item, dict) else str(item)
                score = LexicalIndex.score(query, text)
                if score > 0:
                    scored.append((score, item))
        scored.sort(key=lambda pair: pair[0], reverse=True)
        return {"query": query, "results": [item for _, item in scored[:top_k]]}


class InProcessKnowledgeBridge:
    """Real lexical search over an injectable in-memory document set —
    `index_document` lets a test (or a real deployment's seed step)
    populate it before querying."""

    def __init__(self, documents: list[dict[str, str]] | None = None) -> None:
        self._documents: list[dict[str, str]] = list(documents or [])

    def index_document(self, title: str, content: str) -> None:
        self._documents.append({"title": title, "content": content})

    async def search(self, *, query: str, top_k: int = 5) -> dict[str, Any]:
        scored = [(LexicalIndex.score(query, d["content"]), d) for d in self._documents]
        scored = [pair for pair in scored if pair[0] > 0]
        scored.sort(key=lambda pair: pair[0], reverse=True)
        return {"query": query, "results": [d for _, d in scored[:top_k]]}


class _EchoAgentBridge:
    """Fallback used when no `AICoreContext` is available (most unit
    tests) — deterministic, no network/LLM dependency."""

    async def run_agent(self, agent_id: str, *, task: str, context: dict[str, Any]) -> dict[str, Any]:
        return {"agent_id": agent_id, "task": task, "result": f"[reference-agent-bridge, no AI Core] would execute: {task}"}


class AICoreAgentBridge:
    """Real behavior: frames the task as "acting as `agent_id`" and asks
    AI Core's execution engine for a genuine LLM completion. This is a
    legitimate, working single-turn agent — a real Agent Platform (see
    this project series' the agent platform) additionally brings planning, tool
    use, multi-turn memory, and reflection on top, which is why this
    stays scoped as a bridge reference rather than pretending to be that
    whole platform."""

    def __init__(self, ai_core: Any):
        self.ai_core = ai_core

    async def run_agent(self, agent_id: str, *, task: str, context: dict[str, Any]) -> dict[str, Any]:
        from ai_core.schemas.enums import Role
        from ai_core.schemas.messages import ChatMessage
        from ai_core.schemas.requests import GenerationRequest

        prompt = f"You are agent '{agent_id}'. Context: {context}\n\nTask: {task}"
        request = GenerationRequest(messages=[ChatMessage(role=Role.USER, content=prompt)])
        response = await self.ai_core.execution_engine.generate(request)
        return {"agent_id": agent_id, "task": task, "result": response.content}


class TemplatePromptBridge:
    """Real `str.format` templating against a registered prompt library
    (`register_template`), optionally followed by a genuine AI Core LLM
    call when `ai_core` is supplied — mirrors what a real Prompt
    Platform bridge (versioned prompts, real rendering, real execution)
    looks like, without vendoring that platform's own storage layer."""

    def __init__(self, *, ai_core: Any | None = None, templates: dict[str, str] | None = None):
        self.ai_core = ai_core
        self._templates: dict[str, str] = dict(templates or {})

    def register_template(self, prompt_id: str, template: str) -> None:
        self._templates[prompt_id] = template

    async def run_prompt(self, prompt_id: str, *, variables: dict[str, Any]) -> dict[str, Any]:
        template = self._templates.get(prompt_id)
        if template is None:
            rendered = f"[prompt '{prompt_id}' — no template registered; variables={variables}]"
        else:
            try:
                rendered = template.format(**variables)
            except KeyError as exc:
                raise NodeExecutionError(f"prompt '{prompt_id}' template references unknown variable {exc}") from exc

        if self.ai_core is None:
            return {"prompt_id": prompt_id, "rendered": rendered, "output": rendered}

        from ai_core.schemas.enums import Role
        from ai_core.schemas.messages import ChatMessage
        from ai_core.schemas.requests import GenerationRequest

        request = GenerationRequest(messages=[ChatMessage(role=Role.USER, content=rendered)])
        response = await self.ai_core.execution_engine.generate(request)
        return {"prompt_id": prompt_id, "rendered": rendered, "output": response.content}


class TextDocumentIntelligenceBridge:
    """Real chunking for plain-text content handed directly via
    `file_ref` (a string of raw text, not a filesystem/object-store
    path — this reference bridge has no I/O layer of its own). Binary
    formats are explicitly out of scope: they route to the Memory
    Platform's real Document Intelligence pipeline in a production
    deployment, and this bridge raises clearly rather than silently
    returning nothing if handed something it can't chunk."""

    def __init__(self, *, chunk_size_words: int = 500):
        self.chunk_size_words = chunk_size_words

    async def parse_document(self, *, file_ref: str, mime_type: str | None = None) -> dict[str, Any]:
        if not isinstance(file_ref, str) or not file_ref.strip():
            raise NodeExecutionError(
                "TextDocumentIntelligenceBridge only handles raw text content passed via 'file_ref'; "
                "binary formats (PDF/DOCX/etc.) require the Memory Platform's real Document Intelligence bridge"
            )
        words = file_ref.split()
        chunks = [
            {"index": i // self.chunk_size_words, "text": " ".join(words[i:i + self.chunk_size_words]),
             "word_count": len(words[i:i + self.chunk_size_words])}
            for i in range(0, len(words), self.chunk_size_words)
        ] if words else []
        return {
            "file_ref": file_ref[:80], "mime_type": mime_type or "text/plain",
            "chunks": chunks, "total_words": len(words),
        }


class FunctionRegistryToolBridge:
    """Real function dispatch backed by an extensible registry of actual
    Python callables — not an unconditional echo. Ships with a handful
    of genuinely working example functions; `register` adds more (the
    same pattern `CustomHandler`'s `handler_key` registry uses for
    workspace-registered node logic)."""

    def __init__(self) -> None:
        self._functions: dict[str, Callable[..., Any]] = {
            "add": lambda a, b: a + b,
            "subtract": lambda a, b: a - b,
            "multiply": lambda a, b: a * b,
            "uppercase": lambda text: text.upper(),
            "lowercase": lambda text: text.lower(),
            "word_count": lambda text: len(text.split()),
        }

    def register(self, name: str, fn: Callable[..., Any] | Callable[..., Awaitable[Any]]) -> None:
        self._functions[name] = fn

    async def call_function(self, function_name: str, *, arguments: dict[str, Any]) -> dict[str, Any]:
        fn = self._functions.get(function_name)
        if fn is None:
            raise NodeExecutionError(f"no function registered for '{function_name}' in the tool bridge")
        try:
            result = fn(**arguments)
            if hasattr(result, "__await__"):
                result = await result
        except TypeError as exc:
            raise NodeExecutionError(f"function '{function_name}' rejected arguments {arguments}: {exc}") from exc
        return {"function_name": function_name, "arguments": arguments, "result": result}


def build_reference_bridge_set(
    *, ai_core: Any | None = None, prompt_templates: dict[str, str] | None = None,
    knowledge_documents: list[dict[str, str]] | None = None,
):
    from workflow_platform.ai_bridges.interfaces import BridgeSet

    return BridgeSet(
        agent=AICoreAgentBridge(ai_core) if ai_core is not None else _EchoAgentBridge(),
        prompt=TemplatePromptBridge(ai_core=ai_core, templates=prompt_templates),
        memory=InProcessMemoryBridge(),
        knowledge=InProcessKnowledgeBridge(knowledge_documents),
        document_intelligence=TextDocumentIntelligenceBridge(),
        tool=FunctionRegistryToolBridge(),
    )
