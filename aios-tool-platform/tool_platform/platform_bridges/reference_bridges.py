"""In-process reference implementations of the platform integration
bridges — real, working behavior with no external service dependency,
the same pattern the Workflow Engine's `ai_bridges/reference_bridges.py`
established for its own upstream bridges.

`InProcessWorkflowBridge` / `InProcessAgentBridge` use an explicit
callback-registration model rather than pretending to make a network
call: `trigger_workflow`/`notify_agent` only succeed for a
workflow_id/agent_id whose callable was registered via `register(...)`
(typically wiring a real Workflow/Agent Platform client in production,
or a test double in tests) — calling for anything else raises
`ToolPlanningError` naming exactly what's missing, rather than silently
no-op-ing or fabricating a response.

`InProcessMemoryBridge` and `InProcessPromptBridge` are fully
functional in-process implementations (real storage, real `{{var}}`
template substitution) since neither needs an external system to be
genuinely useful standalone."""
from __future__ import annotations

import re
from typing import Any, Callable

from tool_platform.core.exceptions import ToolPlanningError

_TEMPLATE_PATTERN = re.compile(r"\{\{\s*([a-zA-Z_][a-zA-Z0-9_]*)\s*\}\}")


class InProcessWorkflowBridge:
    def __init__(self) -> None:
        self._callbacks: dict[str, Callable[..., Any]] = {}

    def register(self, workflow_id: str, callback: Callable[..., Any]) -> None:
        self._callbacks[workflow_id] = callback

    async def trigger_workflow(self, workflow_id: str, *, input_variables: dict[str, Any]) -> dict[str, Any]:
        callback = self._callbacks.get(workflow_id)
        if callback is None:
            raise ToolPlanningError(
                f"no workflow integration registered for workflow_id '{workflow_id}' — wire a real "
                "Workflow Platform client (or a test double) via InProcessWorkflowBridge.register()"
            )
        return await callback(input_variables=input_variables)


class InProcessAgentBridge:
    def __init__(self) -> None:
        self._callbacks: dict[str, Callable[..., Any]] = {}

    def register(self, agent_id: str, callback: Callable[..., Any]) -> None:
        self._callbacks[agent_id] = callback

    async def notify_agent(self, agent_id: str, *, message: str, context: dict[str, Any]) -> None:
        callback = self._callbacks.get(agent_id)
        if callback is None:
            raise ToolPlanningError(
                f"no agent integration registered for agent_id '{agent_id}' — wire a real Agent Platform "
                "client (or a test double) via InProcessAgentBridge.register()"
            )
        await callback(message=message, context=context)


class InProcessMemoryBridge:
    def __init__(self) -> None:
        self._store: dict[str, list[dict[str, Any]]] = {}

    async def write_result(self, scope: str, content: dict[str, Any]) -> dict[str, Any]:
        self._store.setdefault(scope, []).append(content)
        return {"scope": scope, "stored": True, "count": len(self._store[scope])}

    async def read_results(self, scope: str) -> list[dict[str, Any]]:
        return list(self._store.get(scope, []))


class InProcessPromptBridge:
    def __init__(self, templates: dict[str, str] | None = None):
        self._templates = dict(templates or {})

    def register_template(self, prompt_id: str, template: str) -> None:
        self._templates[prompt_id] = template

    async def render_prompt(self, prompt_id: str, variables: dict[str, Any]) -> str:
        template = self._templates.get(prompt_id)
        if template is None:
            raise ToolPlanningError(f"no prompt template registered under prompt_id '{prompt_id}'")
        return _TEMPLATE_PATTERN.sub(lambda m: str(variables.get(m.group(1), m.group(0))), template)


def build_reference_bridge_set(*, templates: dict[str, str] | None = None):
    from tool_platform.platform_bridges.interfaces import PlatformBridgeSet

    return PlatformBridgeSet(
        workflow=InProcessWorkflowBridge(), agent=InProcessAgentBridge(),
        memory=InProcessMemoryBridge(), prompt=InProcessPromptBridge(templates),
    )
