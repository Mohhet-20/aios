"""Tests for the container image registry lifecycle: build -> scan ->
sign -> publish, critical-finding blocking, retry, deprecate/
quarantine, and version retention pruning."""
from __future__ import annotations

import pytest

from infra_platform.config.settings import Settings
from infra_platform.containers.image_service import ImageRegistryService
from infra_platform.core.exceptions import ImageScanFailedError, InvalidTransitionError

TENANT = "tenant-containers"


@pytest.mark.asyncio
async def test_happy_path_build_scan_sign_publish(repos):
    service = ImageRegistryService(repos, settings=Settings())
    image = await service.create_image(TENANT, repository="aios/agent-platform", tag="1.0.0")
    assert image.status == "building"

    image = await service.start_scan(TENANT, image.id)
    assert image.status == "scanning"

    await service.record_scan_result(TENANT, image.id, severity="low", finding_count=2, summary="minor CVEs")

    image = await service.sign_image(TENANT, image.id, signer="ci-bot", signature="sig-abc")
    assert image.status == "signed"
    assert image.signed is True

    image = await service.publish_image(TENANT, image.id)
    assert image.status == "published"


@pytest.mark.asyncio
async def test_critical_finding_blocks_publish(repos):
    service = ImageRegistryService(repos, settings=Settings(image_scan_critical_block=True))
    image = await service.create_image(TENANT, repository="aios/tool-platform", tag="2.0.0")
    image = await service.start_scan(TENANT, image.id)

    with pytest.raises(ImageScanFailedError):
        await service.record_scan_result(TENANT, image.id, severity="critical", finding_count=1, summary="RCE vulnerability")

    refreshed = await repos.container_images.get(image.id)
    assert refreshed.status == "scan_failed"

    with pytest.raises(InvalidTransitionError):
        await service.sign_image(TENANT, image.id, signer="ci-bot", signature="sig-xyz")


@pytest.mark.asyncio
async def test_critical_finding_does_not_block_when_setting_disabled(repos):
    service = ImageRegistryService(repos, settings=Settings(image_scan_critical_block=False))
    image = await service.create_image(TENANT, repository="aios/evaluation-platform", tag="3.0.0")
    image = await service.start_scan(TENANT, image.id)
    await service.record_scan_result(TENANT, image.id, severity="critical", finding_count=1, summary="informational only")
    refreshed = await repos.container_images.get(image.id)
    assert refreshed.status == "scanning"  # not blocked, still awaiting explicit sign


@pytest.mark.asyncio
async def test_retry_build_from_scan_failed(repos):
    service = ImageRegistryService(repos, settings=Settings(image_scan_critical_block=True))
    image = await service.create_image(TENANT, repository="aios/memory-platform", tag="4.0.0")
    image = await service.start_scan(TENANT, image.id)
    with pytest.raises(ImageScanFailedError):
        await service.record_scan_result(TENANT, image.id, severity="critical", finding_count=1)

    image = await service.retry_build(TENANT, image.id)
    assert image.status == "building"


@pytest.mark.asyncio
async def test_deprecate_and_quarantine(repos):
    service = ImageRegistryService(repos, settings=Settings())
    image = await service.create_image(TENANT, repository="aios/workflow-engine", tag="5.0.0")
    image = await service.start_scan(TENANT, image.id)
    await service.record_scan_result(TENANT, image.id, severity="low", finding_count=0)
    image = await service.sign_image(TENANT, image.id, signer="ci-bot", signature="sig-1")
    image = await service.publish_image(TENANT, image.id)

    image = await service.deprecate_image(TENANT, image.id)
    assert image.status == "deprecated"

    image = await service.quarantine_image(TENANT, image.id)
    assert image.status == "quarantined"

    with pytest.raises(InvalidTransitionError):
        await service.deprecate_image(TENANT, image.id)


@pytest.mark.asyncio
async def test_prune_old_versions_keeps_only_retention_count(repos):
    service = ImageRegistryService(repos, settings=Settings(image_version_retention_count=2))
    for i in range(4):
        image = await service.create_image(TENANT, repository="aios/prompt-platform", tag=f"{i}.0.0")
        image = await service.start_scan(TENANT, image.id)
        await service.record_scan_result(TENANT, image.id, severity="low", finding_count=0)
        image = await service.sign_image(TENANT, image.id, signer="ci-bot", signature=f"sig-{i}")
        await service.publish_image(TENANT, image.id)

    pruned = await service.prune_old_versions(TENANT, "aios/prompt-platform")
    assert pruned == 2

    remaining = await service.list_versions(TENANT, "aios/prompt-platform")
    assert len(remaining) == 2
