from __future__ import annotations

from sqlalchemy import func, select

from identity_platform.models.session import LoginHistoryModel, SessionModel
from identity_platform.repositories.base import SQLAlchemyRepository


class SessionRepository(SQLAlchemyRepository[SessionModel]):
    model = SessionModel

    async def get_by_refresh_token_hash(self, token_hash: str) -> SessionModel | None:
        stmt = select(SessionModel).where(SessionModel.refresh_token_hash == token_hash)
        return (await self.session.execute(stmt)).scalars().first()

    async def list_active_for_user(self, user_id: str) -> list[SessionModel]:
        stmt = select(SessionModel).where(SessionModel.user_id == user_id, SessionModel.status == "active").order_by(SessionModel.last_used_at.desc())
        return list((await self.session.execute(stmt)).scalars().all())

    async def count_active_for_user(self, user_id: str) -> int:
        stmt = select(func.count()).where(SessionModel.user_id == user_id, SessionModel.status == "active")
        return (await self.session.execute(stmt)).scalar_one()

    async def list_expired_active(self, *, older_than) -> list[SessionModel]:
        stmt = select(SessionModel).where(SessionModel.status == "active", SessionModel.expires_at <= older_than)
        return list((await self.session.execute(stmt)).scalars().all())


class LoginHistoryRepository(SQLAlchemyRepository[LoginHistoryModel]):
    model = LoginHistoryModel

    async def list_for_user(self, user_id: str, *, limit: int = 100) -> list[LoginHistoryModel]:
        stmt = select(LoginHistoryModel).where(LoginHistoryModel.user_id == user_id).order_by(LoginHistoryModel.created_at.desc()).limit(limit)
        return list((await self.session.execute(stmt)).scalars().all())

    async def count_recent_failures(self, email: str, *, since) -> int:
        stmt = select(func.count()).where(
            LoginHistoryModel.email_attempted == email, LoginHistoryModel.success.is_(False), LoginHistoryModel.created_at >= since,
        )
        return (await self.session.execute(stmt)).scalar_one()
