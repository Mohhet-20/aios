"""build_auth_headers: turns a decrypted credential's secret material
into the actual HTTP auth a connector (Task 107's `connectors/`) needs
to inject — the "Secure Token Injection" half of the spec's
AUTHENTICATION section. Kept as pure functions with no DB/session
access so a connector can call this with whatever `VaultService.get_secret`
handed it, without needing a repository."""
from __future__ import annotations

from tool_platform.core.exceptions import CredentialError
from tool_platform.domain.enums import CredentialType


def build_auth_headers(credential_type: str, secret_material: dict) -> dict[str, str]:
    ctype = CredentialType(credential_type)
    if ctype == CredentialType.API_KEY:
        header_name = secret_material.get("header_name", "X-Api-Key")
        return {header_name: secret_material["api_key"]}
    if ctype in (CredentialType.OAUTH2, CredentialType.JWT, CredentialType.BEARER_TOKEN):
        token = secret_material.get("access_token") or secret_material.get("token")
        if not token:
            raise CredentialError(f"{ctype.value} credential is missing an access token")
        return {"Authorization": f"Bearer {token}"}
    if ctype == CredentialType.SERVICE_ACCOUNT:
        return {"Authorization": f"Bearer {secret_material.get('token', '')}"}
    if ctype == CredentialType.MANAGED:
        # A managed credential's shape is connector-specific (e.g. a DB
        # connection string) — no generic header to build.
        return {}
    raise CredentialError(f"unsupported credential type: {credential_type}")
