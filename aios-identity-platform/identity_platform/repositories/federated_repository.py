from __future__ import annotations

from sqlalchemy import select

from identity_platform.models.federated import ExternalIdentityModel
from identity_platform.repositories.base import SQLAlchemyRepository


class ExternalIdentityRepository(SQLAlchemyRepository[ExternalIdentityModel]):
    model = ExternalIdentityModel

    async def get_by_provider_identity(self, provider_key: str, provider_user_id: str) -> ExternalIdentityModel | None:
        stmt = select(ExternalIdentityModel).where(
            ExternalIdentityModel.provider_key == provider_key, ExternalIdentityModel.provider_user_id == provider_user_id,
        )
        return (await self.session.execute(stmt)).scalars().first()

    async def list_for_user(self, user_id: str) -> list[ExternalIdentityModel]:
        stmt = select(ExternalIdentityModel).where(ExternalIdentityModel.user_id == user_id)
        return list((await self.session.execute(stmt)).scalars().all())
