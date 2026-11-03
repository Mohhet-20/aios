"""Protocol translation config management: one row per (route,
translation pair), get-or-create by that identity since a route only
needs one active translation configuration per pair regardless of how
many times a caller re-registers it. Status is a simple two-state
field (active/inactive) guarded directly in-service -- no dedicated
domain entity, the same "simpler status fields" precedent used
elsewhere in this platform for resources with a trivial lifecycle."""
from __future__ import annotations

from gateway_platform.config.settings import Settings, get_settings
from gateway_platform.core.exceptions import TranslationConfigNotFoundError, UnsupportedTranslationPairError
from gateway_platform.models.protocols import ProtocolTranslationConfigModel
from gateway_platform.repositories.registry import RepositoryRegistry


class ProtocolTranslationConfigService:
    def __init__(self, repos: RepositoryRegistry, *, settings: Settings | None = None):
        self.repos = repos
        self.settings = settings or get_settings()

    def _assert_supported(self, translation_pair: str) -> None:
        if translation_pair not in self.settings.protocol_translation_pairs:
            raise UnsupportedTranslationPairError(f"'{translation_pair}' is not a supported translation pair")

    async def register_config(
        self, tenant_id: str, route_id: str, *, translation_pair: str, config: dict | None = None,
    ) -> ProtocolTranslationConfigModel:
        self._assert_supported(translation_pair)
        for existing in await self.repos.protocol_translations.list_for_route(tenant_id, route_id):
            if existing.translation_pair == translation_pair:
                return existing
        record = ProtocolTranslationConfigModel(
            tenant_id=tenant_id, route_id=route_id, translation_pair=translation_pair,
            status="active", config=config or {},
        )
        return await self.repos.protocol_translations.add(record)

    async def activate_config(self, tenant_id: str, config_id: str) -> ProtocolTranslationConfigModel:
        record = await self._get_or_404(tenant_id, config_id)
        record.status = "active"
        return await self.repos.protocol_translations.update(record)

    async def deactivate_config(self, tenant_id: str, config_id: str) -> ProtocolTranslationConfigModel:
        record = await self._get_or_404(tenant_id, config_id)
        record.status = "inactive"
        return await self.repos.protocol_translations.update(record)

    async def list_for_route(self, tenant_id: str, route_id: str) -> list[ProtocolTranslationConfigModel]:
        return await self.repos.protocol_translations.list_for_route(tenant_id, route_id)

    async def get_active_for_pair(
        self, tenant_id: str, route_id: str, translation_pair: str,
    ) -> ProtocolTranslationConfigModel:
        for record in await self.repos.protocol_translations.list_for_route(tenant_id, route_id):
            if record.translation_pair == translation_pair and record.status == "active":
                return record
        raise TranslationConfigNotFoundError(
            f"no active '{translation_pair}' translation config for route '{route_id}'"
        )

    async def _get_or_404(self, tenant_id: str, config_id: str) -> ProtocolTranslationConfigModel:
        record = await self.repos.protocol_translations.get_or_404(config_id)
        if record.tenant_id != tenant_id:
            raise TranslationConfigNotFoundError(f"translation config '{config_id}' not found for tenant '{tenant_id}'")
        return record
