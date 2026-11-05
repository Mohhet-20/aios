"""Test suite & test case management. `register_suite` is a
get-or-create keyed on (tenant_id, name) behind a commit-spanning
`asyncio.Lock` — the same pattern established across every other AIOS
services for check-then-act races that span multiple statements: the
lock must still be held when `session.commit()` runs, or a second
caller waiting on the lock can acquire it and query before the first
caller's insert is durably visible to a separate DB connection."""
from __future__ import annotations

import asyncio
from collections import defaultdict

from quality_platform.config.settings import get_settings
from quality_platform.core.exceptions import TestCaseNotFoundError, TestSuiteNotFoundError, UnsupportedTestTypeError
from quality_platform.models.testing import TestCaseModel, TestSuiteModel
from quality_platform.repositories.registry import RepositoryRegistry


class TestSuiteService:
    _register_locks: dict[str, asyncio.Lock] = defaultdict(asyncio.Lock)

    def __init__(self, repos: RepositoryRegistry):
        self.repos = repos
        self.settings = get_settings()

    def _validate_test_type(self, test_type: str) -> None:
        if test_type not in self.settings.test_pyramid_types:
            raise UnsupportedTestTypeError(f"Unsupported test type '{test_type}'")

    async def get_suite_or_404(self, tenant_id: str, suite_id: str) -> TestSuiteModel:
        suite = await self.repos.test_suites.get_or_404(suite_id)
        if suite.tenant_id != tenant_id:
            raise TestSuiteNotFoundError(f"Test suite '{suite_id}' not found for tenant '{tenant_id}'")
        return suite

    async def get_case_or_404(self, tenant_id: str, case_id: str) -> TestCaseModel:
        case = await self.repos.test_cases.get_or_404(case_id)
        if case.tenant_id != tenant_id:
            raise TestCaseNotFoundError(f"Test case '{case_id}' not found for tenant '{tenant_id}'")
        return case

    async def register_suite(
        self, tenant_id: str, *, name: str, test_type: str, description: str | None = None
    ) -> TestSuiteModel:
        self._validate_test_type(test_type)
        lock_key = f"{tenant_id}:{name}"
        async with self._register_locks[lock_key]:
            existing = await self.repos.test_suites.get_by_name(tenant_id, name)
            if existing is not None:
                return existing
            suite = TestSuiteModel(
                tenant_id=tenant_id, name=name, test_type=test_type, description=description, status="active"
            )
            suite = await self.repos.test_suites.add(suite)
            await self.repos.session.commit()
            return suite

    async def deactivate_suite(self, tenant_id: str, suite_id: str) -> TestSuiteModel:
        suite = await self.get_suite_or_404(tenant_id, suite_id)
        suite.status = "inactive"
        return await self.repos.test_suites.update(suite)

    async def list_suites(self, tenant_id: str, *, test_type: str | None = None) -> list[TestSuiteModel]:
        return await self.repos.test_suites.list_for_tenant(tenant_id, test_type=test_type)

    async def add_case(
        self, tenant_id: str, suite_id: str, *, name: str, test_type: str, config: dict | None = None, tags: list | None = None
    ) -> TestCaseModel:
        await self.get_suite_or_404(tenant_id, suite_id)
        self._validate_test_type(test_type)
        case = TestCaseModel(
            tenant_id=tenant_id, suite_id=suite_id, name=name, test_type=test_type,
            config=config or {}, tags=tags or [], status="active",
        )
        return await self.repos.test_cases.add(case)

    async def list_cases(self, tenant_id: str, suite_id: str) -> list[TestCaseModel]:
        await self.get_suite_or_404(tenant_id, suite_id)
        return await self.repos.test_cases.list_for_suite(tenant_id, suite_id)
