from __future__ import annotations

from sqlalchemy import select

from identity_platform.models.invitation import InvitationModel
from identity_platform.repositories.base import SQLAlchemyRepository


class InvitationRepository(SQLAlchemyRepository[InvitationModel]):
    model = InvitationModel

    async def get_by_token_hash(self, token_hash: str) -> InvitationModel | None:
        stmt = select(InvitationModel).where(InvitationModel.token_hash == token_hash)
        return (await self.session.execute(stmt)).scalars().first()

    async def list_for_organization(self, organization_id: str, *, status: str | None = None) -> list[InvitationModel]:
        stmt = select(InvitationModel).where(InvitationModel.organization_id == organization_id)
        if status:
            stmt = stmt.where(InvitationModel.status == status)
        return list((await self.session.execute(stmt)).scalars().all())

    async def get_pending_for_email(self, organization_id: str, email: str) -> InvitationModel | None:
        stmt = select(InvitationModel).where(
            InvitationModel.organization_id == organization_id, InvitationModel.email == email, InvitationModel.status == "pending",
        )
        return (await self.session.execute(stmt)).scalars().first()

    async def list_expired_pending(self, *, older_than) -> list[InvitationModel]:
        stmt = select(InvitationModel).where(InvitationModel.status == "pending", InvitationModel.expires_at <= older_than)
        return list((await self.session.execute(stmt)).scalars().all())
