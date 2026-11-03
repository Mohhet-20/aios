"""Tool Registry: maps tool names to (ToolDefinition, handler) pairs. The
handler is an async callable `async def handler(**kwargs) -> Any`; the
registry doesn't care what it does, only that it's callable and matches
the definition's declared name.
"""
from __future__ import annotations

from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import Any

from ai_core.schemas.tools import ToolDefinition
from ai_core.utils.exceptions import ToolNotFoundError

ToolHandler = Callable[..., Awaitable[Any]]


@dataclass
class ToolRegistryEntry:
    definition: ToolDefinition
    handler: ToolHandler


class ToolRegistry:
    def __init__(self) -> None:
        self._entries: dict[str, ToolRegistryEntry] = {}

    def register(self, definition: ToolDefinition, handler: ToolHandler) -> None:
        self._entries[definition.name] = ToolRegistryEntry(definition=definition, handler=handler)

    def unregister(self, name: str) -> None:
        self._entries.pop(name, None)

    def get(self, name: str) -> ToolRegistryEntry:
        entry = self._entries.get(name)
        if entry is None:
            raise ToolNotFoundError(f"no tool registered with name '{name}'")
        return entry

    def definitions(self) -> list[ToolDefinition]:
        return [e.definition for e in self._entries.values()]

    def __contains__(self, name: str) -> bool:
        return name in self._entries
