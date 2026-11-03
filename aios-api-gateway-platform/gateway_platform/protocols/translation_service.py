"""Protocol translation orchestration: looks up the active config for
a route + pair, then dispatches to the matching stateless transformer
in `transformers.py`. This is the module's single entry point --
callers never invoke a transformer function directly, so the "which
config applies" lookup can't be bypassed."""
from __future__ import annotations

from typing import Any

from gateway_platform.core.exceptions import UnsupportedTranslationPairError
from gateway_platform.protocols.config_service import ProtocolTranslationConfigService
from gateway_platform.protocols.transformers import (
    REQUEST_TRANSFORMERS,
    RESPONSE_TRANSFORMERS,
    translate_auth,
    translate_version,
)
from gateway_platform.repositories.registry import RepositoryRegistry


class ProtocolTranslationService:
    def __init__(self, repos: RepositoryRegistry, *, config_service: ProtocolTranslationConfigService | None = None):
        self.repos = repos
        self.configs = config_service or ProtocolTranslationConfigService(repos)

    async def translate_request(
        self, tenant_id: str, route_id: str, *, translation_pair: str, payload: dict[str, Any],
    ) -> dict[str, Any]:
        transformer = REQUEST_TRANSFORMERS.get(translation_pair)
        if transformer is None:
            raise UnsupportedTranslationPairError(f"'{translation_pair}' has no registered request transformer")
        config = await self.configs.get_active_for_pair(tenant_id, route_id, translation_pair)
        return transformer(payload, config.config)

    async def translate_response(
        self, tenant_id: str, route_id: str, *, translation_pair: str, payload: dict[str, Any],
    ) -> dict[str, Any]:
        transformer = RESPONSE_TRANSFORMERS.get(translation_pair)
        if transformer is None:
            raise UnsupportedTranslationPairError(f"'{translation_pair}' has no registered response transformer")
        config = await self.configs.get_active_for_pair(tenant_id, route_id, translation_pair)
        return transformer(payload, config.config)

    @staticmethod
    def translate_version(payload: dict[str, Any], *, field_renames: dict[str, str] | None = None, field_removals: list[str] | None = None) -> dict[str, Any]:
        return translate_version(payload, {"field_renames": field_renames or {}, "field_removals": field_removals or []})

    @staticmethod
    def translate_auth(headers: dict[str, str], *, auth_mode: str, api_key_header: str = "X-API-Key") -> dict[str, str]:
        return translate_auth(headers, {"auth_mode": auth_mode, "api_key_header": api_key_header})
