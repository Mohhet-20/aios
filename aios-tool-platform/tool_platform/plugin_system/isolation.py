"""PluginIsolationPolicy: the "can't do more than it declared" boundary
between a plugin and the workspace it's installed into. A plugin's
manifest declares the capabilities its tools need (network_access,
code_execution, read_file, ...); this policy is what a workspace admin
consults before installing to decide whether to allow it, and what the
Execution Engine (Task 106) consults again at call time so an installed
plugin can never quietly exercise a capability beyond what was declared
and approved — the actual resource/network enforcement for those
capabilities is the Sandbox's job (`sandbox/`), this module only ever
answers "is this plugin allowed to even ask for that."""
from __future__ import annotations

from tool_platform.core.exceptions import PluginIsolationError


class PluginIsolationPolicy:
    def validate_capabilities(self, declared_capabilities: list[str], *, workspace_allowed_capabilities: list[str] | None) -> None:
        """`workspace_allowed_capabilities=None` means "no restriction
        configured" (allow anything) — an explicit empty list means "deny
        everything not in it," which is the secure-by-default posture a
        workspace can opt into."""
        if workspace_allowed_capabilities is None:
            return
        disallowed = [c for c in declared_capabilities if c not in workspace_allowed_capabilities]
        if disallowed:
            raise PluginIsolationError(
                f"plugin declares capabilities not permitted in this workspace: {sorted(disallowed)}"
            )

    def requires_sandbox(self, declared_capabilities: list[str]) -> bool:
        return bool({"code_execution", "network_access"} & set(declared_capabilities))
