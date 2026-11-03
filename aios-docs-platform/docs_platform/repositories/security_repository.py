from __future__ import annotations

from sqlalchemy import select

from docs_platform.models.security import RoleAssignmentModel
from docs_platform.repositories.base import SQLAlchemyRepository


class RoleAssignmentRepository(SQLAlchemyRepository[RoleAssignmentModel]):
    model = RoleAssignmentModel

    async def get_for_user(self, tenant_id: str, user_id: str, *, scope_ref: str | None = None) -> RoleAssignmentModel | None:
        stmt = select(RoleAssignmentModel).where(
            RoleAssignmentModel.tenant_id == tenant_id, RoleAssignmentModel.user_id == user_id, RoleAssignmentModel.scope_ref == scope_ref,
        )
        return (await self.session.execute(stmt)).scalars().first()

    async def list_for_user(self, tenant_id: str, user_id: str) -> list[RoleAssignmentModel]:
        stmt = select(RoleAssignmentModel).where(RoleAssignmentModel.tenant_id == tenant_id, RoleAssignmentModel.user_id == user_id)
        return list((await self.session.execute(stmt)).scalars().all())
