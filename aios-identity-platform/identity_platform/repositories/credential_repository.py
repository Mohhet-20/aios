from __future__ import annotations

from sqlalchemy import select

from identity_platform.models.credentials import (
    EmailVerificationTokenModel,
    MagicLinkTokenModel,
    PasswordCredentialModel,
    PasswordResetTokenModel,
)
from identity_platform.repositories.base import SQLAlchemyRepository


class PasswordCredentialRepository(SQLAlchemyRepository[PasswordCredentialModel]):
    model = PasswordCredentialModel

    async def get_for_user(self, user_id: str) -> PasswordCredentialModel | None:
        stmt = select(PasswordCredentialModel).where(PasswordCredentialModel.user_id == user_id)
        return (await self.session.execute(stmt)).scalars().first()


class EmailVerificationTokenRepository(SQLAlchemyRepository[EmailVerificationTokenModel]):
    model = EmailVerificationTokenModel

    async def get_by_token_hash(self, token_hash: str) -> EmailVerificationTokenModel | None:
        stmt = select(EmailVerificationTokenModel).where(EmailVerificationTokenModel.token_hash == token_hash)
        return (await self.session.execute(stmt)).scalars().first()


class PasswordResetTokenRepository(SQLAlchemyRepository[PasswordResetTokenModel]):
    model = PasswordResetTokenModel

    async def get_by_token_hash(self, token_hash: str) -> PasswordResetTokenModel | None:
        stmt = select(PasswordResetTokenModel).where(PasswordResetTokenModel.token_hash == token_hash)
        return (await self.session.execute(stmt)).scalars().first()


class MagicLinkTokenRepository(SQLAlchemyRepository[MagicLinkTokenModel]):
    model = MagicLinkTokenModel

    async def get_by_token_hash(self, token_hash: str) -> MagicLinkTokenModel | None:
        stmt = select(MagicLinkTokenModel).where(MagicLinkTokenModel.token_hash == token_hash)
        return (await self.session.execute(stmt)).scalars().first()
