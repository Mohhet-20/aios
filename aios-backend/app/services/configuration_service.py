"""ConfigurationService — organization-level runtime configuration
(governance policy toggles, feature flags), distinct from the static,
process-wide `app.config.settings.Settings`. Precedence: an explicit
per-organization override always wins; otherwise callers get `default`.
This is the backing store for the Administration page's policy switches
(e.g. "require SSO", "enforce evaluation gating").
"""

from __future__ import annotations

from typing import Any

from app.models.configuration import ConfigurationSettingModel
from app.repositories.configuration_repository import ConfigurationRepository


class ConfigurationService:
    def __init__(self, repository: ConfigurationRepository):
        self.repository = repository

    async def get(self, organization_id: str, key: str, default: Any = None) -> Any:
        row = await self.repository.get_by_key(organization_id, key)
        return row.value.get("value", default) if row else default

    async def set(self, organization_id: str, key: str, value: Any) -> ConfigurationSettingModel:
        row = await self.repository.get_by_key(organization_id, key)
        if row:
            row.value = {"value": value}
            return await self.repository.update(row)
        row = ConfigurationSettingModel(organization_id=organization_id, key=key, value={"value": value})
        return await self.repository.add(row)

    async def list_all(self, organization_id: str) -> list[ConfigurationSettingModel]:
        return await self.repository.list(organization_id=organization_id)
