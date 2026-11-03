"""Plugin isolation policy evaluation: given a plugin version's
declared manifest permissions (from `plugin_sdk/manifest.py`) and a
tenant's isolation policy (an optional allowlist and/or denylist of
permission strings), decide whether the plugin is safe to install —
before it ever runs. This is policy *evaluation*, not runtime sandbox
enforcement: actually isolating a running plugin's process/network
access is out of scope for this control plane, the same disclosed
boundary the Tool Platform's own sandbox module drew around real OS-
level isolation versus this platform's policy modeling."""
from __future__ import annotations

from dataclasses import dataclass, field

from developer_platform.core.exceptions import PermissionDeniedError


@dataclass
class IsolationDecision:
    allowed: bool
    violations: list[str] = field(default_factory=list)


class PluginIsolationService:
    def evaluate(
        self, manifest_permissions: list[str], *, allowed_permissions: list[str] | None = None,
        denied_permissions: list[str] | None = None,
    ) -> IsolationDecision:
        denied = set(denied_permissions or [])
        allowlist = set(allowed_permissions) if allowed_permissions is not None else None

        violations = [p for p in manifest_permissions if p in denied]
        if allowlist is not None:
            violations.extend(p for p in manifest_permissions if p not in allowlist and p not in violations)

        return IsolationDecision(allowed=not violations, violations=sorted(set(violations)))

    def assert_installable(
        self, manifest_permissions: list[str], *, allowed_permissions: list[str] | None = None,
        denied_permissions: list[str] | None = None,
    ) -> IsolationDecision:
        decision = self.evaluate(
            manifest_permissions, allowed_permissions=allowed_permissions, denied_permissions=denied_permissions,
        )
        if not decision.allowed:
            raise PermissionDeniedError(f"plugin requests disallowed permission(s): {decision.violations}")
        return decision
