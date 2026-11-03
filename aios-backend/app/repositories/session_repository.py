from app.models.session import ApiKeyModel, RefreshTokenModel
from app.repositories.base import SQLAlchemyRepository


class RefreshTokenRepository(SQLAlchemyRepository[RefreshTokenModel]):
    model = RefreshTokenModel

    async def get_by_jti(self, jti: str) -> RefreshTokenModel | None:
        results = await self.list(jti=jti)
        return results[0] if results else None


class ApiKeyRepository(SQLAlchemyRepository[ApiKeyModel]):
    model = ApiKeyModel

    async def get_by_hashed_key(self, hashed_key: str) -> ApiKeyModel | None:
        results = await self.list(hashed_key=hashed_key)
        return results[0] if results else None
