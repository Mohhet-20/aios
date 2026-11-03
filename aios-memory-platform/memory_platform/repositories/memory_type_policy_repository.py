from __future__ import annotations

from sqlalchemy import select

from memory_platform.models.memory_type_policy import MemoryTypePolicyModel
from memory_platform.repositories.base import SQLAlchemyRepository


class MemoryTypePolicyRepository(SQLAlchemyRepository[MemoryTypePolicyModel]):
    model = MemoryTypePolicyModel

    async def get_by_key(self, key: str) -> MemoryTypePolicyModel | None:
        stmt = select(MemoryTypePolicyModel).where(MemoryTypePolicyModel.key == key)
        return (await self.session.execute(stmt)).scalars().first()

    async def list_all(self) -> list[MemoryTypePolicyModel]:
        stmt = select(MemoryTypePolicyModel).order_by(MemoryTypePolicyModel.name)
        return list((await self.session.execute(stmt)).scalars().all())
