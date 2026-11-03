"""Sandboxing seam. `NullToolSandbox` runs handlers in-process with no
isolation — fine for first-party tools the platform itself ships. Real
tool sandboxing (subprocess isolation, seccomp/gVisor, network policy,
resource/time limits enforced at the OS level rather than just an asyncio
timeout) is an infrastructure-level concern that plugs in here without
`ToolExecutor` changing: implement `ToolSandbox.run()` against whatever
isolation mechanism production needs and pass it to `ToolExecutor`.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from ai_core.tool_calling.registry import ToolHandler


class ToolSandbox(ABC):
    @abstractmethod
    async def run(self, handler: ToolHandler, arguments: dict) -> Any: ...


class NullToolSandbox(ToolSandbox):
    async def run(self, handler: ToolHandler, arguments: dict) -> Any:
        return await handler(**arguments)
