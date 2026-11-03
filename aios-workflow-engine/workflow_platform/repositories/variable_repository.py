from __future__ import annotations

from sqlalchemy import select

from workflow_platform.models.variable import VariableModel
from workflow_platform.repositories.base import SQLAlchemyRepository


class VariableRepository(SQLAlchemyRepository[VariableModel]):
    model = VariableModel

    async def get_by_key(self, scope_type: str, scope_id: str, key: str) -> VariableModel | None:
        stmt = select(VariableModel).where(
            VariableModel.scope_type == scope_type,
            VariableModel.scope_id == scope_id,
            VariableModel.key == key,
        )
        return (await self.session.execute(stmt)).scalars().first()

    async def list_for_scope(self, scope_type: str, scope_id: str) -> list[VariableModel]:
        stmt = select(VariableModel).where(
            VariableModel.scope_type == scope_type, VariableModel.scope_id == scope_id
        )
        return list((await self.session.execute(stmt)).scalars().all())
