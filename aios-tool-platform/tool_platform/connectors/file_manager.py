"""FileManagerHandler: real read/write/list against a scoped base
directory — the filesystem-restriction half of the Sandbox spec. Every
path in `input_data` is resolved relative to `config["base_dir"]` and
checked (via `Path.resolve()`) to still be inside it after resolution,
so `../../etc/passwd`-style traversal can't escape the sandboxed
directory."""
from __future__ import annotations

from pathlib import Path
from typing import Any

from tool_platform.core.exceptions import ToolExecutionError
from tool_platform.tool_execution.context import ToolCallContext
from tool_platform.tool_execution.handlers.base import ConnectorHandler


class FileManagerHandler(ConnectorHandler):
    def _resolve(self, ctx: ToolCallContext, relative_path: str) -> Path:
        base_dir = Path(ctx.config.get("base_dir", ".")).resolve()
        candidate = (base_dir / relative_path).resolve()
        if base_dir not in candidate.parents and candidate != base_dir:
            raise ToolExecutionError(f"path '{relative_path}' escapes the sandboxed base directory")
        return candidate

    async def execute(self, ctx: ToolCallContext) -> dict[str, Any]:
        operation = ctx.input_data.get("operation", "read")
        path = ctx.input_data.get("path")
        if not path:
            raise ToolExecutionError("file_manager tool call requires 'path'")
        resolved = self._resolve(ctx, path)

        if operation == "read":
            if not resolved.exists():
                raise ToolExecutionError(f"'{path}' does not exist")
            return {"content": resolved.read_text(), "size_bytes": resolved.stat().st_size}
        if operation == "write":
            content = ctx.input_data.get("content", "")
            resolved.parent.mkdir(parents=True, exist_ok=True)
            resolved.write_text(content)
            return {"written_bytes": len(content.encode("utf-8"))}
        if operation == "list":
            if not resolved.exists():
                raise ToolExecutionError(f"'{path}' does not exist")
            return {"entries": sorted(p.name for p in resolved.iterdir())}
        if operation == "delete":
            if resolved.exists():
                resolved.unlink()
            return {"deleted": True}
        raise ToolExecutionError(f"unsupported file_manager operation: '{operation}'")
