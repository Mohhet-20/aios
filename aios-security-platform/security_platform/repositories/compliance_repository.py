from __future__ import annotations

from sqlalchemy import select

from security_platform.models.compliance import (
    ComplianceEvidenceModel,
    ComplianceFrameworkConfigModel,
    ConsentRecordModel,
    DataResidencyRecordModel,
    LegalHoldModel,
    RetentionPolicyModel,
)
from security_platform.repositories.base import SQLAlchemyRepository


class ComplianceFrameworkConfigRepository(SQLAlchemyRepository[ComplianceFrameworkConfigModel]):
    model = ComplianceFrameworkConfigModel

    async def get_for_framework(self, tenant_id: str, framework: str) -> ComplianceFrameworkConfigModel | None:
        stmt = select(ComplianceFrameworkConfigModel).where(
            ComplianceFrameworkConfigModel.tenant_id == tenant_id, ComplianceFrameworkConfigModel.framework == framework
        )
        return (await self.session.execute(stmt)).scalars().first()

    async def list_enabled(self, tenant_id: str) -> list[ComplianceFrameworkConfigModel]:
        stmt = select(ComplianceFrameworkConfigModel).where(
            ComplianceFrameworkConfigModel.tenant_id == tenant_id, ComplianceFrameworkConfigModel.is_enabled.is_(True)
        )
        return list((await self.session.execute(stmt)).scalars().all())


class ComplianceEvidenceRepository(SQLAlchemyRepository[ComplianceEvidenceModel]):
    model = ComplianceEvidenceModel

    async def list_for_framework(self, tenant_id: str, framework: str, *, limit: int = 500) -> list[ComplianceEvidenceModel]:
        stmt = (
            select(ComplianceEvidenceModel)
            .where(ComplianceEvidenceModel.tenant_id == tenant_id, ComplianceEvidenceModel.framework == framework)
            .order_by(ComplianceEvidenceModel.collected_at.desc())
            .limit(limit)
        )
        return list((await self.session.execute(stmt)).scalars().all())


class RetentionPolicyRepository(SQLAlchemyRepository[RetentionPolicyModel]):
    model = RetentionPolicyModel

    async def get_for_resource(self, tenant_id: str, resource_type: str) -> RetentionPolicyModel | None:
        stmt = select(RetentionPolicyModel).where(
            RetentionPolicyModel.tenant_id == tenant_id, RetentionPolicyModel.resource_type == resource_type
        )
        return (await self.session.execute(stmt)).scalars().first()

    async def list_for_tenant(self, tenant_id: str) -> list[RetentionPolicyModel]:
        stmt = select(RetentionPolicyModel).where(RetentionPolicyModel.tenant_id == tenant_id)
        return list((await self.session.execute(stmt)).scalars().all())


class LegalHoldRepository(SQLAlchemyRepository[LegalHoldModel]):
    model = LegalHoldModel

    async def list_active_for_resource(self, tenant_id: str, resource_type: str, resource_id: str) -> list[LegalHoldModel]:
        stmt = select(LegalHoldModel).where(
            LegalHoldModel.tenant_id == tenant_id,
            LegalHoldModel.resource_type == resource_type,
            LegalHoldModel.resource_id == resource_id,
            LegalHoldModel.status == "active",
        )
        return list((await self.session.execute(stmt)).scalars().all())

    async def list_active(self, tenant_id: str) -> list[LegalHoldModel]:
        stmt = select(LegalHoldModel).where(LegalHoldModel.tenant_id == tenant_id, LegalHoldModel.status == "active")
        return list((await self.session.execute(stmt)).scalars().all())


class ConsentRecordRepository(SQLAlchemyRepository[ConsentRecordModel]):
    model = ConsentRecordModel

    async def get_active_for_subject(self, tenant_id: str, subject_id: str, purpose: str) -> ConsentRecordModel | None:
        stmt = select(ConsentRecordModel).where(
            ConsentRecordModel.tenant_id == tenant_id,
            ConsentRecordModel.subject_id == subject_id,
            ConsentRecordModel.purpose == purpose,
            ConsentRecordModel.status == "granted",
        )
        return (await self.session.execute(stmt)).scalars().first()

    async def list_for_subject(self, tenant_id: str, subject_id: str) -> list[ConsentRecordModel]:
        stmt = select(ConsentRecordModel).where(
            ConsentRecordModel.tenant_id == tenant_id, ConsentRecordModel.subject_id == subject_id
        )
        return list((await self.session.execute(stmt)).scalars().all())


class DataResidencyRecordRepository(SQLAlchemyRepository[DataResidencyRecordModel]):
    model = DataResidencyRecordModel

    async def get_for_resource(self, tenant_id: str, resource_type: str, resource_id: str) -> DataResidencyRecordModel | None:
        stmt = select(DataResidencyRecordModel).where(
            DataResidencyRecordModel.tenant_id == tenant_id,
            DataResidencyRecordModel.resource_type == resource_type,
            DataResidencyRecordModel.resource_id == resource_id,
        )
        return (await self.session.execute(stmt)).scalars().first()
