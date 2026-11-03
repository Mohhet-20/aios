import pytest

from quality_platform.core.exceptions import TestSuiteNotFoundError, UnsupportedTestTypeError
from quality_platform.testing.test_suite_service import TestSuiteService

pytestmark = pytest.mark.asyncio


async def test_register_suite_creates_new(repos):
    svc = TestSuiteService(repos)
    suite = await svc.register_suite("t1", name="unit-suite", test_type="unit")
    assert suite.status == "active"
    assert suite.test_type == "unit"


async def test_register_suite_rejects_unsupported_type(repos):
    svc = TestSuiteService(repos)
    with pytest.raises(UnsupportedTestTypeError):
        await svc.register_suite("t1", name="bad-suite", test_type="not-a-type")


async def test_get_suite_or_404_cross_tenant(repos):
    svc = TestSuiteService(repos)
    suite = await svc.register_suite("t1", name="tenant-suite", test_type="unit")
    with pytest.raises(TestSuiteNotFoundError):
        await svc.get_suite_or_404("t2", suite.id)


async def test_add_case_and_list(repos):
    svc = TestSuiteService(repos)
    suite = await svc.register_suite("t1", name="case-suite", test_type="integration")
    case = await svc.add_case("t1", suite.id, name="case-1", test_type="integration", tags=["smoke"])
    cases = await svc.list_cases("t1", suite.id)
    assert len(cases) == 1
    assert cases[0].id == case.id
    assert cases[0].tags == ["smoke"]


async def test_deactivate_suite(repos):
    svc = TestSuiteService(repos)
    suite = await svc.register_suite("t1", name="deact-suite", test_type="unit")
    updated = await svc.deactivate_suite("t1", suite.id)
    assert updated.status == "inactive"
