from __future__ import annotations

from sqlalchemy import select

from security_platform.models.secrets import (
    EncryptionKeyModel,
    SecretAccessLogModel,
    SecretAccessPolicyModel,
    SecretModel,
    SecretVersionModel,
)
from security_platform.repositories.base import SQLAlchemyRepository


class SecretRepository(SQLAlchemyRepository[SecretModel]):
    model = SecretModel

    async def get_by_name(self, tenant_id: str, name: str) -> SecretModel | None:
        stmt = select(SecretModel).where(
            SecretModel.tenant_id == tenant_id, SecretModel.name == name, SecretModel.is_deleted.is_(False)
        )
        return (await self.session.execute(stmt)).scalars().first()

    async def list_for_tenant(self, tenant_id: str) -> list[SecretModel]:
        stmt = select(SecretModel).where(SecretModel.tenant_id == tenant_id, SecretModel.is_deleted.is_(False))
        return list((await self.session.execute(stmt)).scalars().all())

    async def count_by_status(self, tenant_id: str) -> dict[str, int]:
        from sqlalchemy import func

        stmt = (
            select(SecretModel.status, func.count())
            .where(SecretModel.tenant_id == tenant_id, SecretModel.is_deleted.is_(False))
            .group_by(SecretModel.status)
        )
        rows = (await self.session.execute(stmt)).all()
        return {s: count for s, count in rows}


class SecretVersionRepository(SQLAlchemyRepository[SecretVersionModel]):
    model = SecretVersionModel

    async def list_for_secret(self, tenant_id: str, secret_id: str) -> list[SecretVersionModel]:
        stmt = (
            select(SecretVersionModel)
            .where(SecretVersionModel.tenant_id == tenant_id, SecretVersionModel.secret_id == secret_id)
            .order_by(SecretVersionModel.version_number.desc())
        )
        return list((await self.session.execute(stmt)).scalars().all())

    async def get_active(self, tenant_id: str, secret_id: str) -> SecretVersionModel | None:
        stmt = select(SecretVersionModel).where(
            SecretVersionModel.tenant_id == tenant_id,
            SecretVersionModel.secret_id == secret_id,
            SecretVersionModel.is_active.is_(True),
        )
        return (await self.session.execute(stmt)).scalars().first()


class SecretAccessPolicyRepository(SQLAlchemyRepository[SecretAccessPolicyModel]):
    model = SecretAccessPolicyModel

    async def get_for_principal(self, tenant_id: str, secret_id: str, principal_id: str) -> SecretAccessPolicyModel | None:
        stmt = select(SecretAccessPolicyModel).where(
            SecretAccessPolicyModel.tenant_id == tenant_id,
            SecretAccessPolicyModel.secret_id == secret_id,
            SecretAccessPolicyModel.principal_id == principal_id,
            SecretAccessPolicyModel.is_deleted.is_(False),
        )
        return (await self.session.execute(stmt)).scalars().first()


class SecretAccessLogRepository(SQLAlchemyRepository[SecretAccessLogModel]):
    model = SecretAccessLogModel

    async def list_for_secret(self, tenant_id: str, secret_id: str, *, limit: int = 200) -> list[SecretAccessLogModel]:
        stmt = (
            select(SecretAccessLogModel)
            .where(SecretAccessLogModel.tenant_id == tenant_id, SecretAccessLogModel.secret_id == secret_id)
            .order_by(SecretAccessLogModel.accessed_at.desc())
            .limit(limit)
        )
        return list((await self.session.execute(stmt)).scalars().all())

    async def count_since(self, tenant_id: str, *, start_time, success: bool | None = None) -> int:
        from sqlalchemy import func

        stmt = select(func.count()).select_from(SecretAccessLogModel).where(
            SecretAccessLogModel.tenant_id == tenant_id, SecretAccessLogModel.accessed_at >= start_time
        )
        if success is not None:
            stmt = stmt.where(SecretAccessLogModel.success.is_(success))
        return (await self.session.execute(stmt)).scalar_one()


class EncryptionKeyRepository(SQLAlchemyRepository[EncryptionKeyModel]):
    model = EncryptionKeyModel

    async def get_active(self, tenant_id: str) -> EncryptionKeyModel | None:
        stmt = select(EncryptionKeyModel).where(
            EncryptionKeyModel.tenant_id == tenant_id, EncryptionKeyModel.status == "active"
        ).order_by(EncryptionKeyModel.created_at.desc())
        return (await self.session.execute(stmt)).scalars().first()

    async def count_by_status(self, tenant_id: str) -> dict[str, int]:
        from sqlalchemy import func

        stmt = (
            select(EncryptionKeyModel.status, func.count())
            .where(EncryptionKeyModel.tenant_id == tenant_id)
            .group_by(EncryptionKeyModel.status)
        )
        rows = (await self.session.execute(stmt)).all()
        return {s: count for s, count in rows}
