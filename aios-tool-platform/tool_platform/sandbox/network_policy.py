"""NetworkPolicy: allow/deny enforcement for outbound network access from
a sandboxed or connector execution. `SandboxNetworkPolicy.DENY_ALL` is
the secure-by-default posture (`settings.sandbox_network_default_deny`);
a tool version opts into `ALLOW_LIST` with explicit hosts, or (rarely,
and only for trusted internal connectors) `ALLOW_ALL`."""
from __future__ import annotations

from dataclasses import dataclass, field
from urllib.parse import urlparse

from tool_platform.core.exceptions import NetworkPolicyViolationError
from tool_platform.domain.enums import SandboxNetworkPolicy


@dataclass(frozen=True)
class NetworkPolicy:
    policy_type: SandboxNetworkPolicy = SandboxNetworkPolicy.DENY_ALL
    allowed_hosts: list[str] = field(default_factory=list)

    def check_url(self, url: str) -> None:
        if self.policy_type == SandboxNetworkPolicy.ALLOW_ALL:
            return
        if self.policy_type == SandboxNetworkPolicy.DENY_ALL:
            raise NetworkPolicyViolationError(f"network access is denied by policy; blocked request to '{url}'")

        host = urlparse(url).hostname
        if host is None or not any(self._host_matches(host, pattern) for pattern in self.allowed_hosts):
            raise NetworkPolicyViolationError(f"host '{host}' is not on the allow-list; blocked request to '{url}'")

    @staticmethod
    def _host_matches(host: str, pattern: str) -> bool:
        host = host.lower()
        pattern = pattern.lower()
        if pattern.startswith("*."):
            return host.endswith(pattern[1:])
        return host == pattern
