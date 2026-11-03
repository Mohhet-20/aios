"""Data-category node handlers. DATABASE_QUERY delegates to an injected
`query_executor` callable rather than hardcoding a driver — the engine
has no opinion on which database a workflow author's query targets, and
hardcoding one would contradict the "coordinates every subsystem, owns
none of them" principle this whole platform is built on. PYTHON_EXECUTION
runs a single safe expression through the same restricted evaluator used
for CONDITION/DECISION routing — real arbitrary-code execution belongs in
a properly sandboxed worker process, an explicit future seam, not an
in-process `exec()` call this platform will never carry."""
from __future__ import annotations

from typing import Any

from workflow_platform.core.exceptions import NodeExecutionError
from workflow_platform.workflow_engine.context import NodeContext
from workflow_platform.workflow_engine.expressions import evaluate_expression
from workflow_platform.workflow_engine.handlers.base import NodeHandler


class DatabaseQueryHandler(NodeHandler):
    async def execute(self, ctx: NodeContext) -> dict[str, Any]:
        executor = ctx.extra.get("query_executor")
        if executor is None:
            raise NodeExecutionError("DATABASE_QUERY node requires a query_executor to be configured on the engine")
        query = ctx.config.get("query")
        params = ctx.config.get("params") or {}
        rows = await executor(query, params)
        return {"rows": rows, "row_count": len(rows) if hasattr(rows, "__len__") else None}


class PythonExecutionHandler(NodeHandler):
    async def execute(self, ctx: NodeContext) -> dict[str, Any]:
        expression = ctx.config.get("expression")
        if not expression:
            raise NodeExecutionError("PYTHON_EXECUTION node requires an 'expression' in its config")
        result = evaluate_expression(expression, ctx.variables)
        output_key = ctx.config.get("output_variable", "result")
        return {output_key: result}


class FileUploadHandler(NodeHandler):
    async def execute(self, ctx: NodeContext) -> dict[str, Any]:
        file_ref = ctx.config.get("file_ref") or ctx.variables.get("file_ref")
        if not file_ref:
            raise NodeExecutionError("FILE_UPLOAD node requires a 'file_ref' in config or context variables")
        return {"file_ref": file_ref}


class FileProcessingHandler(NodeHandler):
    async def execute(self, ctx: NodeContext) -> dict[str, Any]:
        file_ref = ctx.config.get("file_ref") or ctx.variables.get("file_ref")
        if not file_ref:
            raise NodeExecutionError("FILE_PROCESSING node requires a 'file_ref' in config or context variables")
        operation = ctx.config.get("operation", "noop")
        return {"file_ref": file_ref, "operation": operation, "processed": True}
