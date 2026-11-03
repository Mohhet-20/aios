"""PythonExecutionHandler / ShellCommandHandler: the two connector
categories that actually run arbitrary code, so they're the two that
always route through `sandbox/subprocess_sandbox.py`'s real rlimit-
enforced subprocess sandbox rather than any in-process `exec()` — a
tool call under these categories can never touch the engine process's
own memory or credentials."""
from __future__ import annotations

from typing import Any

from tool_platform.core.exceptions import ToolExecutionError
from tool_platform.sandbox.resource_limits import ResourceLimits
from tool_platform.sandbox.subprocess_sandbox import SubprocessSandbox
from tool_platform.tool_execution.context import ToolCallContext
from tool_platform.tool_execution.handlers.base import ConnectorHandler


def _limits_from_ctx(ctx: ToolCallContext) -> ResourceLimits:
    cfg = ctx.config
    return ResourceLimits(
        cpu_seconds=cfg.get("cpu_seconds", ResourceLimits().cpu_seconds),
        memory_mb=cfg.get("memory_mb", ResourceLimits().memory_mb),
        disk_mb=cfg.get("disk_mb", ResourceLimits().disk_mb),
        timeout_seconds=cfg.get("sandbox_timeout_seconds", ctx.execution.timeout_seconds or ResourceLimits().timeout_seconds),
    )


class PythonExecutionHandler(ConnectorHandler):
    def __init__(self, *, sandbox: SubprocessSandbox | None = None):
        self._sandbox = sandbox or SubprocessSandbox()

    async def execute(self, ctx: ToolCallContext) -> dict[str, Any]:
        code = ctx.input_data.get("code") or ctx.config.get("code")
        if not code:
            raise ToolExecutionError("python_execution tool call requires 'code'")
        result = self._sandbox.run_python(code, input_data=ctx.input_data.get("args"), limits=_limits_from_ctx(ctx))
        if result.timed_out:
            raise ToolExecutionError(f"python execution timed out after {_limits_from_ctx(ctx).timeout_seconds}s")
        if not result.success:
            raise ToolExecutionError(f"python execution failed (exit {result.return_code}): {result.stderr[-500:]}")
        return {
            "stdout": result.stdout, "stderr": result.stderr, "return_code": result.return_code,
            "cpu_seconds": result.cpu_seconds, "peak_memory_mb": result.peak_memory_mb,
        }


class ShellCommandHandler(ConnectorHandler):
    def __init__(self, *, sandbox: SubprocessSandbox | None = None):
        self._sandbox = sandbox or SubprocessSandbox()

    async def execute(self, ctx: ToolCallContext) -> dict[str, Any]:
        command = ctx.input_data.get("command") or ctx.config.get("command")
        if not command:
            raise ToolExecutionError("shell_command tool call requires 'command' (a list of argv strings)")
        if isinstance(command, str):
            command = command.split()
        result = self._sandbox.run_shell(command, limits=_limits_from_ctx(ctx))
        if result.timed_out:
            raise ToolExecutionError(f"shell command timed out after {_limits_from_ctx(ctx).timeout_seconds}s")
        if not result.success:
            raise ToolExecutionError(f"shell command failed (exit {result.return_code}): {result.stderr[-500:]}")
        return {"stdout": result.stdout, "stderr": result.stderr, "return_code": result.return_code}
