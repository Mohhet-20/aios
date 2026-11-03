"""Tests for Model Lifecycle Management: registry entries, guarded
version stage transitions, approval-gated promotion (both the
approval-required and auto-approve paths), lineage, and retention
pruning of archived versions."""
from __future__ import annotations

import pytest

from infra_platform.config.settings import Settings
from infra_platform.core.exceptions import InvalidTransitionError, ModelRegistryError, ModelVersionNotFoundError, NotFoundError
from infra_platform.model_registry.registry_service import (
    ModelLineageService,
    ModelRegistryService,
    ModelVersionService,
)

TENANT = "tenant-models"


@pytest.mark.asyncio
async def test_register_model_rejects_duplicate_name(repos):
    service = ModelRegistryService(repos)
    await service.register_model(TENANT, name="fraud-classifier")
    with pytest.raises(ModelRegistryError):
        await service.register_model(TENANT, name="fraud-classifier")


@pytest.mark.asyncio
async def test_create_version_increments_version_number(repos):
    registry_service = ModelRegistryService(repos)
    version_service = ModelVersionService(repos)
    model = await registry_service.register_model(TENANT, name="churn-model")

    v1 = await version_service.create_version(TENANT, model.id, metrics={"auc": 0.81})
    v2 = await version_service.create_version(TENANT, model.id, metrics={"auc": 0.85})
    assert v1.version_number == 1
    assert v2.version_number == 2
    assert v1.stage == "development"


@pytest.mark.asyncio
async def test_promotion_requires_approval_by_default(repos):
    registry_service = ModelRegistryService(repos)
    version_service = ModelVersionService(repos, settings=Settings(model_promotion_requires_approval=True))
    model = await registry_service.register_model(TENANT, name="pricing-model")
    version = await version_service.create_version(TENANT, model.id)

    approval = await version_service.request_promotion(TENANT, version.id, requested_stage="staging")
    assert approval.status == "pending"

    refreshed = await version_service._get_version(TENANT, version.id)
    assert refreshed.stage == "development"  # not yet promoted

    approval = await version_service.decide_approval(TENANT, approval.id, approved=True, reviewer_id="reviewer-1")
    assert approval.status == "approved"
    assert approval.decided_at is not None

    refreshed = await version_service._get_version(TENANT, version.id)
    assert refreshed.stage == "staging"

    with pytest.raises(ModelRegistryError):
        await version_service.decide_approval(TENANT, approval.id, approved=True)


@pytest.mark.asyncio
async def test_promotion_auto_applies_when_approval_not_required(repos):
    registry_service = ModelRegistryService(repos)
    version_service = ModelVersionService(repos, settings=Settings(model_promotion_requires_approval=False))
    model = await registry_service.register_model(TENANT, name="recommender")
    version = await version_service.create_version(TENANT, model.id)

    approval = await version_service.request_promotion(TENANT, version.id, requested_stage="staging")
    assert approval.status == "approved"

    refreshed = await version_service._get_version(TENANT, version.id)
    assert refreshed.stage == "staging"


@pytest.mark.asyncio
async def test_promotion_to_production_sets_current_production_pointer(repos):
    registry_service = ModelRegistryService(repos)
    version_service = ModelVersionService(repos, settings=Settings(model_promotion_requires_approval=False))
    model = await registry_service.register_model(TENANT, name="ranking-model")
    version = await version_service.create_version(TENANT, model.id)

    await version_service.request_promotion(TENANT, version.id, requested_stage="staging")
    await version_service.request_promotion(TENANT, version.id, requested_stage="production")

    model_after = await registry_service.get(TENANT, model.id)
    assert model_after.current_production_version_id == version.id


@pytest.mark.asyncio
async def test_illegal_stage_skip_raises(repos):
    registry_service = ModelRegistryService(repos)
    version_service = ModelVersionService(repos, settings=Settings(model_promotion_requires_approval=False))
    model = await registry_service.register_model(TENANT, name="skip-model")
    version = await version_service.create_version(TENANT, model.id)

    with pytest.raises(InvalidTransitionError):
        await version_service.request_promotion(TENANT, version.id, requested_stage="production")


@pytest.mark.asyncio
async def test_unknown_stage_name_raises(repos):
    registry_service = ModelRegistryService(repos)
    version_service = ModelVersionService(repos)
    model = await registry_service.register_model(TENANT, name="typo-model")
    version = await version_service.create_version(TENANT, model.id)
    with pytest.raises(ModelRegistryError):
        await version_service.request_promotion(TENANT, version.id, requested_stage="prooduction")


@pytest.mark.asyncio
async def test_version_not_found_raises(repos):
    version_service = ModelVersionService(repos)
    with pytest.raises(ModelVersionNotFoundError):
        await version_service.archive_version(TENANT, "no-such-version")


@pytest.mark.asyncio
async def test_lineage_recording(repos):
    registry_service = ModelRegistryService(repos)
    version_service = ModelVersionService(repos)
    lineage_service = ModelLineageService(repos)
    model = await registry_service.register_model(TENANT, name="lineage-model")
    version = await version_service.create_version(TENANT, model.id)

    await lineage_service.record_lineage(TENANT, version.id, parent_type="experiment_run", parent_ref_id="run-123")
    await lineage_service.record_lineage(TENANT, version.id, parent_type="dataset", parent_ref_id="ds-456")

    edges = await lineage_service.list_for_version(TENANT, version.id)
    assert {e.parent_type for e in edges} == {"experiment_run", "dataset"}


@pytest.mark.asyncio
async def test_prune_old_archived_versions(repos):
    registry_service = ModelRegistryService(repos)
    version_service = ModelVersionService(repos, settings=Settings(model_version_retention_count=1))
    model = await registry_service.register_model(TENANT, name="prune-model")

    versions = []
    for _ in range(3):
        v = await version_service.create_version(TENANT, model.id)
        versions.append(v)
        await version_service.archive_version(TENANT, v.id)

    pruned = await version_service.prune_old_versions(TENANT, model.id)
    assert pruned == 2

    remaining = await version_service.list_for_model(TENANT, model.id)
    assert len(remaining) == 1
    assert remaining[0].version_number == 3  # newest retained


@pytest.mark.asyncio
async def test_create_version_unknown_model_raises(repos):
    version_service = ModelVersionService(repos)
    with pytest.raises(NotFoundError):
        await version_service.create_version(TENANT, "no-such-model")
