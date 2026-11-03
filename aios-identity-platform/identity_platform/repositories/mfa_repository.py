from __future__ import annotations

from sqlalchemy import select

from identity_platform.models.mfa import MfaFactorModel, RecoveryCodeModel, TrustedDeviceModel
from identity_platform.repositories.base import SQLAlchemyRepository


class MfaFactorRepository(SQLAlchemyRepository[MfaFactorModel]):
    model = MfaFactorModel

    async def list_for_user(self, user_id: str) -> list[MfaFactorModel]:
        stmt = select(MfaFactorModel).where(MfaFactorModel.user_id == user_id)
        return list((await self.session.execute(stmt)).scalars().all())

    async def get_active_for_user(self, user_id: str) -> MfaFactorModel | None:
        stmt = select(MfaFactorModel).where(MfaFactorModel.user_id == user_id, MfaFactorModel.status == "active")
        return (await self.session.execute(stmt)).scalars().first()


class RecoveryCodeRepository(SQLAlchemyRepository[RecoveryCodeModel]):
    model = RecoveryCodeModel

    async def list_unused_for_user(self, user_id: str) -> list[RecoveryCodeModel]:
        stmt = select(RecoveryCodeModel).where(RecoveryCodeModel.user_id == user_id, RecoveryCodeModel.used_at.is_(None))
        return list((await self.session.execute(stmt)).scalars().all())

    async def get_by_code_hash(self, code_hash: str) -> RecoveryCodeModel | None:
        stmt = select(RecoveryCodeModel).where(RecoveryCodeModel.code_hash == code_hash)
        return (await self.session.execute(stmt)).scalars().first()


class TrustedDeviceRepository(SQLAlchemyRepository[TrustedDeviceModel]):
    model = TrustedDeviceModel

    async def get_by_token_hash(self, token_hash: str) -> TrustedDeviceModel | None:
        stmt = select(TrustedDeviceModel).where(TrustedDeviceModel.token_hash == token_hash)
        return (await self.session.execute(stmt)).scalars().first()

    async def list_for_user(self, user_id: str) -> list[TrustedDeviceModel]:
        stmt = select(TrustedDeviceModel).where(TrustedDeviceModel.user_id == user_id)
        return list((await self.session.execute(stmt)).scalars().all())
