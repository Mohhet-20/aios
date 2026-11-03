"""OAuth-ready architecture: this platform's API keys already carry a
`scopes` list shaped exactly like OAuth scope grants, so the seam a
real OAuth2 authorization-code flow would plug into is scope
negotiation — given what a client requests and what's actually been
granted, decide whether the request is satisfiable. `validate_scopes`
is that real, testable piece; issuing authorization codes, exchanging
them for tokens, and talking to a real identity provider are the
disclosed gap (the same posture the MCP Integration module takes
toward a live transport, and the Kubernetes module takes toward a real
cluster)."""
from __future__ import annotations

from developer_platform.core.exceptions import PermissionDeniedError

WILDCARD_SCOPE = "*"


class OAuthReadinessService:
    def validate_scopes(self, requested: list[str], granted: list[str]) -> None:
        if WILDCARD_SCOPE in granted:
            return
        missing = [scope for scope in requested if scope not in granted]
        if missing:
            raise PermissionDeniedError(f"requested scope(s) not granted: {missing}")

    def narrow_scopes(self, requested: list[str], granted: list[str]) -> list[str]:
        """Returns the intersection of requested and granted scopes —
        the effective scope set a real token-exchange step would embed
        in the issued access token."""
        if WILDCARD_SCOPE in granted:
            return list(requested)
        return [scope for scope in requested if scope in granted]
