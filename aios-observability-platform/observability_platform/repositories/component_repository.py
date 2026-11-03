from __future__ import annotations

from sqlalchemy import select

from observability_platform.models.components import ComponentModel
from observability_platform.repositories.base import SQLAlchemyRepository


class ComponentRepository(SQLAlchemyRepository[ComponentModel]):
    model = ComponentModel

    async def list_for_tenant(self, tenant_id: str, *, component_type: str | None = None) -> list[ComponentModel]:
        stmt = select(ComponentModel).where(
            ComponentModel.tenant_id == tenant_id, ComponentModel.is_deleted.is_(False)
        )
        if component_type:
            stmt = stmt.where(ComponentModel.component_type == component_type)
        return list((await self.session.execute(stmt)).scalars().all())
