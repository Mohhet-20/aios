"""Plugin extensibility mechanism.

A `PluginManifest` is the contract a third-party (or internal) package
declares to extend AIOS — new tools, new graders, new agent archetypes —
without modifying core engine code, per the architecture blueprint's
extensibility principle. `PluginRegistry` is an in-process catalog today;
`PluginService` (application layer) is what persists install/enable state
to the database via `PluginModel`. Loading real third-party code from a
manifest (dynamic import, sandboxing) is intentionally not implemented here
— that's a security-sensitive feature deserving its own dedicated design
pass, not a few lines bolted onto the backend.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Protocol


class PluginCapability(Protocol):
    """Marker protocol every plugin capability (tool, grader, agent
    archetype) must satisfy: a stable id and a human name. Concrete
    capability types (ToolDefinition, GraderDefinition, ...) extend this
    with their own fields."""

    id: str
    name: str


@dataclass
class PluginManifest:
    id: str
    name: str
    version: str
    category: str
    description: str = ""
    provides_tools: list[str] = field(default_factory=list)
    provides_graders: list[str] = field(default_factory=list)


class PluginRegistry:
    def __init__(self) -> None:
        self._manifests: dict[str, PluginManifest] = {}

    def register(self, manifest: PluginManifest) -> None:
        self._manifests[manifest.id] = manifest

    def get(self, plugin_id: str) -> PluginManifest | None:
        return self._manifests.get(plugin_id)

    def all(self) -> list[PluginManifest]:
        return list(self._manifests.values())


plugin_registry = PluginRegistry()

# Built-in example manifests, registered at import time so `GET
# /api/v1/plugins/available` has something real to return even before any
# organization has installed anything.
plugin_registry.register(
    PluginManifest(
        id="core.zendesk",
        name="Zendesk Connector",
        version="2.4.0",
        category="Support",
        description="Read/update tickets in Zendesk.",
        provides_tools=["zendesk_search", "zendesk_update_ticket"],
    )
)
plugin_registry.register(
    PluginManifest(
        id="core.github",
        name="GitHub Integration",
        version="1.9.2",
        category="Engineering",
        description="Read PRs, post review comments.",
        provides_tools=["github_read_pr", "github_post_comment"],
    )
)
plugin_registry.register(
    PluginManifest(
        id="core.custom_grader_sdk",
        name="Custom Grader SDK",
        version="0.6.0-beta",
        category="Evaluation",
        description="Author custom LLM-as-judge graders.",
        provides_graders=["custom_rubric_grader"],
    )
)
