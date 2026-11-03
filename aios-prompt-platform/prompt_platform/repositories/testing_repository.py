from __future__ import annotations

from sqlalchemy import select

from prompt_platform.models.testing import GoldenTestCaseModel, TestResultModel, TestRunModel
from prompt_platform.repositories.base import SQLAlchemyRepository


class GoldenTestCaseRepository(SQLAlchemyRepository[GoldenTestCaseModel]):
    model = GoldenTestCaseModel

    async def list_for_prompt(self, prompt_id: str) -> list[GoldenTestCaseModel]:
        return await self.list(filters={"prompt_id": prompt_id})


class TestRunRepository(SQLAlchemyRepository[TestRunModel]):
    model = TestRunModel

    async def list_for_prompt(self, prompt_id: str, *, limit: int = 50) -> list[TestRunModel]:
        stmt = select(TestRunModel).where(TestRunModel.prompt_id == prompt_id).order_by(
            TestRunModel.started_at.desc()
        ).limit(limit)
        return list((await self.session.execute(stmt)).scalars().all())


class TestResultRepository(SQLAlchemyRepository[TestResultModel]):
    model = TestResultModel

    async def list_for_run(self, test_run_id: str) -> list[TestResultModel]:
        stmt = select(TestResultModel).where(TestResultModel.test_run_id == test_run_id)
        return list((await self.session.execute(stmt)).scalars().all())
