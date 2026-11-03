from app.models.configuration import ConfigurationSettingModel
from app.repositories.base import SQLAlchemyRepository


class ConfigurationRepository(SQLAlchemyRepository[ConfigurationSettingModel]):
    model = ConfigurationSettingModel

    async def get_by_key(self, organization_id: str, key: str) -> ConfigurationSettingModel | None:
        results = await self.list(organization_id=organization_id, key=key)
        return results[0] if results else None
