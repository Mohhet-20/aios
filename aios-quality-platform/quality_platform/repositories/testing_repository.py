from __future__ import annotations

from sqlalchemy import select

from quality_platform.models.testing import TestCaseModel, TestCaseResultModel, TestRunModel, TestSuiteModel
from quality_platform.repositories.base import SQLAlchemyRepository


class TestSuiteRepository(SQLAlchemyRepository[TestSuiteModel]):
    model = TestSuiteModel

    async def get_by_name(self, tenant_id: str, name: str) -> TestSuiteModel | None:
        stmt = select(TestSuiteModel).where(
            TestSuiteModel.tenant_id == tenant_id, TestSuiteModel.name == name, TestSuiteModel.is_deleted.is_(False),
        )
        return (await self.session.execute(stmt)).scalars().first()

    async def list_for_tenant(self, tenant_id: str, *, test_type: str | None = None) -> list[TestSuiteModel]:
        stmt = select(TestSuiteModel).where(
            TestSuiteModel.tenant_id == tenant_id, TestSuiteModel.is_deleted.is_(False),
        )
        if test_type:
            stmt = stmt.where(TestSuiteModel.test_type == test_type)
        return list((await self.session.execute(stmt)).scalars().all())


class TestCaseRepository(SQLAlchemyRepository[TestCaseModel]):
    model = TestCaseModel

    async def list_for_suite(self, tenant_id: str, suite_id: str) -> list[TestCaseModel]:
        stmt = select(TestCaseModel).where(
            TestCaseModel.tenant_id == tenant_id, TestCaseModel.suite_id == suite_id, TestCaseModel.is_deleted.is_(False),
        )
        return list((await self.session.execute(stmt)).scalars().all())


class TestRunRepository(SQLAlchemyRepository[TestRunModel]):
    model = TestRunModel

    async def list_for_suite(self, tenant_id: str, suite_id: str, *, limit: int = 100) -> list[TestRunModel]:
        stmt = select(TestRunModel).where(
            TestRunModel.tenant_id == tenant_id, TestRunModel.suite_id == suite_id,
        ).order_by(TestRunModel.requested_at.desc()).limit(limit)
        return list((await self.session.execute(stmt)).scalars().all())


class TestCaseResultRepository(SQLAlchemyRepository[TestCaseResultModel]):
    model = TestCaseResultModel

    async def list_for_run(self, tenant_id: str, test_run_id: str) -> list[TestCaseResultModel]:
        stmt = select(TestCaseResultModel).where(
            TestCaseResultModel.tenant_id == tenant_id, TestCaseResultModel.test_run_id == test_run_id,
        )
        return list((await self.session.execute(stmt)).scalars().all())

    async def list_for_case(self, tenant_id: str, test_case_id: str, *, limit: int = 50) -> list[TestCaseResultModel]:
        stmt = select(TestCaseResultModel).where(
            TestCaseResultModel.tenant_id == tenant_id, TestCaseResultModel.test_case_id == test_case_id,
        ).order_by(TestCaseResultModel.recorded_at.desc()).limit(limit)
        return list((await self.session.execute(stmt)).scalars().all())
