"""Tests for the Feature Store: feature group + feature CRUD,
versioning, validation rules, publish-gating for online-enabled
groups, and value validation."""
from __future__ import annotations

import pytest

from infra_platform.config.settings import Settings
from infra_platform.core.exceptions import FeatureNotFoundError, FeatureStoreError, FeatureValidationError, NotFoundError
from infra_platform.feature_store.feature_store_service import FeatureGroupService, FeatureService

TENANT = "tenant-features"


@pytest.mark.asyncio
async def test_create_feature_group_rejects_duplicate(repos):
    service = FeatureGroupService(repos)
    await service.create_feature_group(TENANT, name="user-features", entity_key="user_id")
    with pytest.raises(FeatureStoreError):
        await service.create_feature_group(TENANT, name="user-features", entity_key="user_id")


@pytest.mark.asyncio
async def test_create_feature_and_new_version(repos):
    group_service = FeatureGroupService(repos)
    feature_service = FeatureService(repos)
    group = await group_service.create_feature_group(TENANT, name="txn-features", entity_key="account_id")

    feature = await feature_service.create_feature(TENANT, group.id, name="avg_txn_amount", value_type="float")
    assert feature.version == 1
    assert feature.status == "draft"

    with pytest.raises(FeatureStoreError):
        await feature_service.create_feature(TENANT, group.id, name="avg_txn_amount", value_type="float")

    v2 = await feature_service.create_new_version(TENANT, group.id, name="avg_txn_amount")
    assert v2.version == 2
    assert v2.status == "draft"


@pytest.mark.asyncio
async def test_new_version_without_prior_raises(repos):
    group_service = FeatureGroupService(repos)
    feature_service = FeatureService(repos)
    group = await group_service.create_feature_group(TENANT, name="empty-group", entity_key="id")
    with pytest.raises(FeatureNotFoundError):
        await feature_service.create_new_version(TENANT, group.id, name="ghost-feature")


@pytest.mark.asyncio
async def test_publish_blocked_without_rules_when_online_enabled(repos):
    group_service = FeatureGroupService(repos)
    feature_service = FeatureService(repos, settings=Settings(feature_validation_required_for_online=True))
    group = await group_service.create_feature_group(TENANT, name="online-group", entity_key="user_id", online_enabled=True)
    feature = await feature_service.create_feature(TENANT, group.id, name="risk_score", value_type="float")

    with pytest.raises(FeatureValidationError):
        await feature_service.publish_feature(TENANT, feature.id)

    await feature_service.add_validation_rule(TENANT, feature.id, rule_type="range", config={"min": 0, "max": 1})
    published = await feature_service.publish_feature(TENANT, feature.id)
    assert published.status == "active"

    with pytest.raises(FeatureStoreError):
        await feature_service.publish_feature(TENANT, feature.id)


@pytest.mark.asyncio
async def test_publish_offline_only_group_does_not_require_rules(repos):
    group_service = FeatureGroupService(repos)
    feature_service = FeatureService(repos, settings=Settings(feature_validation_required_for_online=True))
    group = await group_service.create_feature_group(
        TENANT, name="offline-group", entity_key="user_id", online_enabled=False, offline_enabled=True
    )
    feature = await feature_service.create_feature(TENANT, group.id, name="lifetime_value", value_type="float")
    published = await feature_service.publish_feature(TENANT, feature.id)
    assert published.status == "active"


@pytest.mark.asyncio
async def test_deprecate_feature(repos):
    group_service = FeatureGroupService(repos)
    feature_service = FeatureService(repos)
    group = await group_service.create_feature_group(TENANT, name="deprecate-group", entity_key="id", online_enabled=False)
    feature = await feature_service.create_feature(TENANT, group.id, name="old_feature", value_type="int")
    await feature_service.publish_feature(TENANT, feature.id)

    deprecated = await feature_service.deprecate_feature(TENANT, feature.id)
    assert deprecated.status == "deprecated"

    with pytest.raises(FeatureStoreError):
        await feature_service.deprecate_feature(TENANT, feature.id)


@pytest.mark.asyncio
async def test_validate_value_not_null_range_regex(repos):
    group_service = FeatureGroupService(repos)
    feature_service = FeatureService(repos)
    group = await group_service.create_feature_group(TENANT, name="validate-group", entity_key="id", online_enabled=False)

    feature = await feature_service.create_feature(TENANT, group.id, name="score", value_type="float")
    await feature_service.add_validation_rule(TENANT, feature.id, rule_type="not_null")
    await feature_service.add_validation_rule(TENANT, feature.id, rule_type="range", config={"min": 0, "max": 100})

    assert await feature_service.validate_value(TENANT, feature.id, 50)
    with pytest.raises(FeatureValidationError):
        await feature_service.validate_value(TENANT, feature.id, None)
    with pytest.raises(FeatureValidationError):
        await feature_service.validate_value(TENANT, feature.id, 150)

    email_feature = await feature_service.create_feature(TENANT, group.id, name="email_domain", value_type="string")
    await feature_service.add_validation_rule(TENANT, email_feature.id, rule_type="regex", config={"pattern": r"^[a-z]+\.com$"})
    assert await feature_service.validate_value(TENANT, email_feature.id, "example.com")
    with pytest.raises(FeatureValidationError):
        await feature_service.validate_value(TENANT, email_feature.id, "not-a-domain")


@pytest.mark.asyncio
async def test_unknown_group_and_feature_raise(repos):
    feature_service = FeatureService(repos)
    with pytest.raises(NotFoundError):
        await feature_service.create_feature(TENANT, "no-such-group", name="x", value_type="int")
    with pytest.raises(FeatureNotFoundError):
        await feature_service.publish_feature(TENANT, "no-such-feature")
