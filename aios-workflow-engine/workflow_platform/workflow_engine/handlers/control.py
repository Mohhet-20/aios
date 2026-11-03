"""Control-flow node handlers. START/END are bookkeeping no-ops (the
engine's routing logic, not these handlers, is what actually makes
DECISION/CONDITION/PARALLEL_BRANCH/MERGE/LOOP branch — these handlers
just record that the node ran and, for DECISION/CONDITION, evaluate and
expose the routing value so the engine's edge-selection can read it back
off `output_data`)."""
from __future__ import annotations

import asyncio
from typing import Any

from workflow_platform.workflow_engine.context import NodeContext
from workflow_platform.workflow_engine.expressions import evaluate_expression
from workflow_platform.workflow_engine.handlers.base import NodeHandler


class StartHandler(NodeHandler):
    async def execute(self, ctx: NodeContext) -> dict[str, Any]:
        return {}


class EndHandler(NodeHandler):
    async def execute(self, ctx: NodeContext) -> dict[str, Any]:
        return {}


class ConditionHandler(NodeHandler):
    async def execute(self, ctx: NodeContext) -> dict[str, Any]:
        expression = ctx.config.get("expression", "True")
        value = bool(evaluate_expression(expression, ctx.variables))
        return {"branch_value": value}


class DecisionHandler(NodeHandler):
    async def execute(self, ctx: NodeContext) -> dict[str, Any]:
        expression = ctx.config.get("expression", "None")
        value = evaluate_expression(expression, ctx.variables)
        return {"branch_value": value}


class ParallelBranchHandler(NodeHandler):
    async def execute(self, ctx: NodeContext) -> dict[str, Any]:
        return {}


class MergeHandler(NodeHandler):
    async def execute(self, ctx: NodeContext) -> dict[str, Any]:
        return {}


class LoopHandler(NodeHandler):
    async def execute(self, ctx: NodeContext) -> dict[str, Any]:
        return {}


class DelayHandler(NodeHandler):
    def __init__(self, *, sleep_fn=asyncio.sleep):
        self._sleep = sleep_fn

    async def execute(self, ctx: NodeContext) -> dict[str, Any]:
        seconds = float(ctx.config.get("seconds", 0))
        await self._sleep(seconds)
        return {"delayed_seconds": seconds}


class WaitHandler(NodeHandler):
    """Pauses for an external signal. The engine itself models this as an
    execution pause (WAITING_APPROVAL-style, driven by
    Execution.request_approval reuse would be wrong semantically, so the
    engine instead just leaves the execution PAUSED and expects an
    external `resume_execution` call once whatever it's waiting on has
    happened) — this handler only records what it's waiting on."""

    async def execute(self, ctx: NodeContext) -> dict[str, Any]:
        return {"waiting_on": ctx.config.get("wait_for", "external_signal")}


class ErrorHandlerHandler(NodeHandler):
    async def execute(self, ctx: NodeContext) -> dict[str, Any]:
        return {"handled_error": ctx.variables.get("__last_error__")}


class RetryHandler(NodeHandler):
    async def execute(self, ctx: NodeContext) -> dict[str, Any]:
        return {"retry_of": ctx.config.get("target_node_key")}
