import pytest

from release_platform.core.exceptions import SbomNotFoundError
from release_platform.security.sbom_service import SbomService

pytestmark = pytest.mark.asyncio

TENANT = "t-security"


async def test_generate_and_list_sbom(repos):
    svc = SbomService(repos)
    await svc.generate_sbom(TENANT, artifact_id="art-1", content_ref="s3://sboms/art-1.json")
    sboms = await svc.list_for_artifact(TENANT, "art-1")
    assert len(sboms) == 1


async def test_assert_sbom_exists_raises_when_required_and_missing(repos):
    svc = SbomService(repos)
    with pytest.raises(SbomNotFoundError):
        await svc.assert_sbom_exists(TENANT, "art-missing")


async def test_assert_sbom_exists_passes_when_present(repos):
    svc = SbomService(repos)
    await svc.generate_sbom(TENANT, artifact_id="art-2")
    await svc.assert_sbom_exists(TENANT, "art-2")
