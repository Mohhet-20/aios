import pytest

from release_platform.core.exceptions import ConflictError, InvalidTransitionError, UnsupportedReleaseChannelError, ValidationError
from release_platform.release_engineering.release_service import ReleaseService

pytestmark = pytest.mark.asyncio

TENANT = "t-release"


async def test_create_release_rejects_unsupported_channel(repos):
    svc = ReleaseService(repos)
    with pytest.raises(UnsupportedReleaseChannelError):
        await svc.create_release(TENANT, version="1.0.0", channel="nightly")


async def test_create_release_rejects_invalid_semver(repos):
    svc = ReleaseService(repos)
    with pytest.raises(ValidationError):
        await svc.create_release(TENANT, version="not-a-version", channel="stable")


async def test_create_release_rejects_duplicate_version(repos):
    svc = ReleaseService(repos)
    await svc.create_release(TENANT, version="1.0.0", channel="stable")
    with pytest.raises(ConflictError):
        await svc.create_release(TENANT, version="1.0.0", channel="stable")


async def test_full_release_lifecycle(repos):
    svc = ReleaseService(repos)
    release = await svc.create_release(TENANT, version="2.0.0", channel="stable")
    assert release.status == "draft"

    release = await svc.submit_for_candidate(TENANT, release.id)
    assert release.status == "candidate"

    release = await svc.approve(TENANT, release.id)
    assert release.status == "approved"

    release = await svc.release(TENANT, release.id)
    assert release.status == "released"
    assert release.released_at is not None

    release = await svc.deprecate(TENANT, release.id)
    assert release.status == "deprecated"


async def test_reject_sends_back_to_draft(repos):
    svc = ReleaseService(repos)
    release = await svc.create_release(TENANT, version="2.1.0", channel="beta")
    release = await svc.submit_for_candidate(TENANT, release.id)
    release = await svc.reject(TENANT, release.id)
    assert release.status == "draft"


async def test_invalid_transition_raises(repos):
    svc = ReleaseService(repos)
    release = await svc.create_release(TENANT, version="2.2.0", channel="beta")
    with pytest.raises(InvalidTransitionError):
        await svc.release(TENANT, release.id)


async def test_yank_only_from_released(repos):
    svc = ReleaseService(repos)
    release = await svc.create_release(TENANT, version="2.3.0", channel="stable")
    release = await svc.submit_for_candidate(TENANT, release.id)
    release = await svc.approve(TENANT, release.id)
    release = await svc.release(TENANT, release.id)
    release = await svc.yank(TENANT, release.id)
    assert release.status == "yanked"


async def test_list_releases_filters_by_channel(repos):
    svc = ReleaseService(repos)
    await svc.create_release(TENANT, version="3.0.0", channel="stable")
    await svc.create_release(TENANT, version="3.0.0-rc.1", channel="rc")
    stable = await svc.list_releases(TENANT, channel="stable")
    assert all(r.channel == "stable" for r in stable)
