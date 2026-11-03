import pytest

from release_platform.release_engineering.release_service import ReleaseService
from release_platform.release_engineering.version_service import VersionService

pytestmark = pytest.mark.asyncio

TENANT = "t-release"


async def test_version_history_recorded_on_create_and_release(repos):
    release_svc = ReleaseService(repos)
    version_svc = VersionService(repos)
    release = await release_svc.create_release(TENANT, version="4.0.0", channel="stable")
    await release_svc.submit_for_candidate(TENANT, release.id)
    await release_svc.approve(TENANT, release.id)
    await release_svc.release(TENANT, release.id)

    history = await version_svc.list_history(TENANT, release.id)
    assert len(history) == 2
    assert history[0].notes == "release created"
    assert history[1].notes == "released"


async def test_compatibility_matrix_check(repos):
    version_svc = VersionService(repos)
    await version_svc.add_compatibility_entry(
        TENANT, version="4.0.0", component_ref="sdk:python", compatible_from="1.0.0", compatible_to="2.0.0"
    )

    assert await version_svc.check_compatible(TENANT, "4.0.0", "sdk:python", "1.5.0") is True
    assert await version_svc.check_compatible(TENANT, "4.0.0", "sdk:python", "3.0.0") is False
    assert await version_svc.check_compatible(TENANT, "4.0.0", "sdk:go", "1.5.0") is False
