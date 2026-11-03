"""Feature Store: feature groups (an entity-keyed collection, e.g.
all features keyed by `user_id`), versioned features within a group
(draft -> active -> deprecated), and validation rules (not_null,
range, regex) that gate a feature going live online.

DISCLOSED SCOPE BOUNDARY: this is a feature *registry* — it tracks
feature definitions, versions, and validation rules, but does not
itself store feature values or serve an online/offline lookup path.
`online_enabled`/`offline_enabled` are declared intent that a real
online store (e.g. Redis) and offline store (e.g. a warehouse table)
would honor; `validate_value` is the reusable rule-checking logic
either serving path would call before writing/serving a value."""
from __future__ import annotations

import re

from infra_platform.config.settings import Settings, get_settings
from infra_platform.core.exceptions import FeatureNotFoundError, FeatureStoreError, FeatureValidationError, NotFoundError
from infra_platform.domain.enums import FeatureStatus
from infra_platform.models.feature_store import FeatureGroupModel, FeatureModel, FeatureValidationRuleModel
from infra_platform.repositories.registry import RepositoryRegistry

_VALID_RULE_TYPES = {"not_null", "range", "regex"}


class FeatureGroupService:
    def __init__(self, repos: RepositoryRegistry):
        self.repos = repos

    async def create_feature_group(
        self, tenant_id: str, *, name: str, entity_key: str, description: str | None = None,
        online_enabled: bool = True, offline_enabled: bool = True,
    ) -> FeatureGroupModel:
        existing = await self.repos.feature_groups.get_by_name(tenant_id, name)
        if existing is not None:
            raise FeatureStoreError(f"Feature group '{name}' already exists")
        group = FeatureGroupModel(
            tenant_id=tenant_id, name=name, description=description, entity_key=entity_key,
            online_enabled=online_enabled, offline_enabled=offline_enabled,
        )
        return await self.repos.feature_groups.add(group)

    async def get(self, tenant_id: str, feature_group_id: str) -> FeatureGroupModel:
        group = await self.repos.feature_groups.get(feature_group_id)
        if group is None or group.tenant_id != tenant_id:
            raise NotFoundError(f"FeatureGroup '{feature_group_id}' not found")
        return group

    async def list_for_tenant(self, tenant_id: str) -> list[FeatureGroupModel]:
        return await self.repos.feature_groups.list_for_tenant(tenant_id)


class FeatureService:
    def __init__(self, repos: RepositoryRegistry, *, settings: Settings | None = None):
        self.repos = repos
        self.settings = settings or get_settings()

    async def _get_group(self, tenant_id: str, feature_group_id: str) -> FeatureGroupModel:
        group = await self.repos.feature_groups.get(feature_group_id)
        if group is None or group.tenant_id != tenant_id:
            raise NotFoundError(f"FeatureGroup '{feature_group_id}' not found")
        return group

    async def _get_feature(self, tenant_id: str, feature_id: str) -> FeatureModel:
        feature = await self.repos.features.get(feature_id)
        if feature is None or feature.tenant_id != tenant_id:
            raise FeatureNotFoundError(f"Feature '{feature_id}' not found")
        return feature

    async def create_feature(
        self, tenant_id: str, feature_group_id: str, *, name: str, value_type: str, description: str | None = None
    ) -> FeatureModel:
        await self._get_group(tenant_id, feature_group_id)
        existing = await self.repos.features.get_by_name_in_group(tenant_id, feature_group_id, name)
        if existing is not None:
            raise FeatureStoreError(f"Feature '{name}' already exists in this group (create a new version instead)")
        feature = FeatureModel(
            tenant_id=tenant_id, feature_group_id=feature_group_id, name=name, value_type=value_type,
            version=1, status=FeatureStatus.DRAFT.value, description=description,
        )
        return await self.repos.features.add(feature)

    async def create_new_version(
        self, tenant_id: str, feature_group_id: str, *, name: str, value_type: str | None = None, description: str | None = None
    ) -> FeatureModel:
        await self._get_group(tenant_id, feature_group_id)
        latest = await self.repos.features.get_by_name_in_group(tenant_id, feature_group_id, name)
        if latest is None:
            raise FeatureNotFoundError(f"Feature '{name}' has no prior version to build on")
        feature = FeatureModel(
            tenant_id=tenant_id, feature_group_id=feature_group_id, name=name,
            value_type=value_type or latest.value_type, version=latest.version + 1,
            status=FeatureStatus.DRAFT.value, description=description if description is not None else latest.description,
        )
        return await self.repos.features.add(feature)

    async def add_validation_rule(
        self, tenant_id: str, feature_id: str, *, rule_type: str, config: dict | None = None
    ) -> FeatureValidationRuleModel:
        await self._get_feature(tenant_id, feature_id)
        if rule_type not in _VALID_RULE_TYPES:
            raise FeatureValidationError(f"Unknown validation rule type '{rule_type}'")
        rule = FeatureValidationRuleModel(tenant_id=tenant_id, feature_id=feature_id, rule_type=rule_type, config=config or {})
        return await self.repos.feature_validation_rules.add(rule)

    async def validate_value(self, tenant_id: str, feature_id: str, value: object) -> bool:
        """Runs every rule attached to a feature against `value`,
        raising `FeatureValidationError` on the first violation."""
        rules = await self.repos.feature_validation_rules.list_for_feature(tenant_id, feature_id)
        for rule in rules:
            if rule.rule_type == "not_null":
                if value is None:
                    raise FeatureValidationError(f"Feature '{feature_id}' value cannot be null")
            elif rule.rule_type == "range":
                if value is None:
                    continue
                minimum = rule.config.get("min")
                maximum = rule.config.get("max")
                if minimum is not None and value < minimum:
                    raise FeatureValidationError(f"Feature '{feature_id}' value {value} below minimum {minimum}")
                if maximum is not None and value > maximum:
                    raise FeatureValidationError(f"Feature '{feature_id}' value {value} above maximum {maximum}")
            elif rule.rule_type == "regex":
                pattern = rule.config.get("pattern", "")
                if pattern and (value is None or not re.match(pattern, str(value))):
                    raise FeatureValidationError(f"Feature '{feature_id}' value '{value}' does not match pattern '{pattern}'")
        return True

    async def publish_feature(self, tenant_id: str, feature_id: str) -> FeatureModel:
        feature = await self._get_feature(tenant_id, feature_id)
        if feature.status != FeatureStatus.DRAFT.value:
            raise FeatureStoreError(f"Feature '{feature_id}' is not draft (status={feature.status})")
        group = await self._get_group(tenant_id, feature.feature_group_id)
        if group.online_enabled and self.settings.feature_validation_required_for_online:
            rules = await self.repos.feature_validation_rules.list_for_feature(tenant_id, feature_id)
            if not rules:
                raise FeatureValidationError(
                    f"Feature '{feature_id}' belongs to an online-enabled group and has no validation rules"
                )
        feature.status = FeatureStatus.ACTIVE.value
        return await self.repos.features.update(feature)

    async def deprecate_feature(self, tenant_id: str, feature_id: str) -> FeatureModel:
        feature = await self._get_feature(tenant_id, feature_id)
        if feature.status == FeatureStatus.DEPRECATED.value:
            raise FeatureStoreError(f"Feature '{feature_id}' is already deprecated")
        feature.status = FeatureStatus.DEPRECATED.value
        return await self.repos.features.update(feature)

    async def list_for_group(self, tenant_id: str, feature_group_id: str) -> list[FeatureModel]:
        return await self.repos.features.list_for_group(tenant_id, feature_group_id)

    async def list_rules(self, tenant_id: str, feature_id: str) -> list[FeatureValidationRuleModel]:
        return await self.repos.feature_validation_rules.list_for_feature(tenant_id, feature_id)
