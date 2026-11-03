import pytest

from release_platform.core.exceptions import (
    InvalidTransitionError,
    NotFoundError,
    UnsupportedUpdateTypeError,
    VersionCompatibilityError,
)
from release_platform.release_engineering.version_service import VersionService
from release_platform.updates.update_service import UpdateJobService

pytestmark = pytest.mark.asyncio

TENANT = "t-updates"


async def test_schedule_update_rejects_unsupported_type(repos):
    svc = UpdateJobService(repos)
    with pytest.raises(UnsupportedUpdateTypeError):
        await svc.schedule_update(TENANT, target_ref="install:1", update_type="telepathic", to_version="1.0.0")


async def test_schedule_update_rejects_invalid_semver(repos):
    svc = UpdateJobService(repos)
    with pytest.raises(UnsupportedUpdateTypeError):
        await svc.schedule_update(TENANT, target_ref="install:1", update_type="automatic", to_version="bogus")


async def test_get_or_404_raises_for_missing(repos):
    svc = UpdateJobService(repos)
    with pytest.raises(NotFoundError):
        await svc.get_or_404(TENANT, "nonexistent-id")


async def test_full_success_lifecycle(repos):
    svc = UpdateJobService(repos)
    job = await svc.schedule_update(TENANT, target_ref="install:2", update_type="automatic", to_version="1.1.0", from_version="1.0.0")
    assert job.status == "queued"

    job = await svc.start_download(TENANT, job.id)
    assert job.status == "downloading"

    job = await svc.begin_apply(TENANT, job.id)
    assert job.status == "applying"

    job = await svc.mark_applied(TENANT, job.id)
    assert job.status == "applied"
    assert job.applied_at is not None

    job = await svc.mark_rolled_back(TENANT, job.id)
    assert job.status == "rolled_back"


async def test_failure_path_records_reason(repos):
    svc = UpdateJobService(repos)
    job = await svc.schedule_update(TENANT, target_ref="install:3", update_type="patch", to_version="1.2.0")
    job = await svc.start_download(TENANT, job.id)
    job = await svc.fail(TENANT, job.id, reason="checksum mismatch")
    assert job.status == "failed"
    assert job.failure_reason == "checksum mismatch"


async def test_cannot_skip_states(repos):
    svc = UpdateJobService(repos)
    job = await svc.schedule_update(TENANT, target_ref="install:4", update_type="manual", to_version="1.3.0")
    with pytest.raises(InvalidTransitionError):
        await svc.mark_applied(TENANT, job.id)


async def test_failed_job_is_terminal(repos):
    svc = UpdateJobService(repos)
    job = await svc.schedule_update(TENANT, target_ref="install:5", update_type="delta", to_version="1.4.0")
    job = await svc.start_download(TENANT, job.id)
    job = await svc.fail(TENANT, job.id, reason="network error")
    with pytest.raises(InvalidTransitionError):
        await svc.mark_rolled_back(TENANT, job.id)


async def test_version_compatibility_check_raises_when_incompatible(repos):
    version_svc = VersionService(repos)
    await version_svc.add_compatibility_entry(TENANT, version="2.0.0", component_ref="sdk:python", compatible_from="1.0.0", compatible_to="1.9.0")
    svc = UpdateJobService(repos)
    with pytest.raises(VersionCompatibilityError):
        await svc.check_version_compatibility(TENANT, platform_version="2.0.0", component_ref="sdk:python", candidate_version="3.0.0")


async def test_version_compatibility_check_passes_when_compatible(repos):
    version_svc = VersionService(repos)
    await version_svc.add_compatibility_entry(TENANT, version="2.1.0", component_ref="sdk:go", compatible_from="1.0.0", compatible_to="1.9.0")
    svc = UpdateJobService(repos)
    await svc.check_version_compatibility(TENANT, platform_version="2.1.0", component_ref="sdk:go", candidate_version="1.5.0")


async def test_list_for_target(repos):
    svc = UpdateJobService(repos)
    await svc.schedule_update(TENANT, target_ref="install:6", update_type="scheduled", to_version="1.5.0")
    await svc.schedule_update(TENANT, target_ref="install:6", update_type="scheduled", to_version="1.6.0")
    jobs = await svc.list_for_target(TENANT, "install:6")
    assert len(jobs) == 2
