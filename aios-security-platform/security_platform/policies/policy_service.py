"""Policy CRUD and lifecycle. Every rules edit is snapshotted into
`PolicyVersionModel` before the live row changes — policy history is
never lost, mirroring the same discipline every other AIOS platform
applies to prompts/workflows/documents it versions."""
from __future__ import annotations

from security_platform.core.exceptions import ValidationError
from security_platform.domain.entities import Policy as PolicyEntity
from security_platform.domain.enums import PolicyEffect, PolicyScope, PolicyStatus
from security_platform.models.policies import PolicyModel, PolicyVersionModel
from security_platform.repositories.registry import RepositoryRegistry


def _to_entity(model: PolicyModel) -> PolicyEntity:
    return PolicyEntity(id=model.id, status=PolicyStatus(model.status))


class PolicyService:
    def __init__(self, repos: RepositoryRegistry):
        self.repos = repos

    async def create_policy(
        self,
        tenant_id: str,
        *,
        name: str,
        scope: str,
        effect: str = PolicyEffect.DENY.value,
        rules: dict | None = None,
        scope_ref_id: str | None = None,
        parent_policy_id: str | None = None,
        priority: int = 100,
        description: str | None = None,
        created_by: str | None = None,
    ) -> PolicyModel:
        if scope not in {s.value for s in PolicyScope}:
            raise ValidationError(f"Unknown policy scope '{scope}'")
        if effect not in {e.value for e in PolicyEffect}:
            raise ValidationError(f"Unknown policy effect '{effect}'")
        policy = PolicyModel(
            tenant_id=tenant_id, name=name, scope=scope, scope_ref_id=scope_ref_id, parent_policy_id=parent_policy_id,
            effect=effect, rules=rules or {}, priority=priority, description=description, created_by=created_by,
        )
        policy = await self.repos.policies.add(policy)
        await self.repos.policy_versions.add(
            PolicyVersionModel(
                tenant_id=tenant_id, policy_id=policy.id, version_number=1,
                rules_snapshot=policy.rules, effect_snapshot=policy.effect, created_by=created_by,
            )
        )
        return policy

    async def update_rules(
        self, tenant_id: str, policy_id: str, *, rules: dict, effect: str | None = None, updated_by: str | None = None
    ) -> PolicyModel:
        policy = await self.repos.policies.get_or_404(policy_id)
        policy.rules = rules
        if effect is not None:
            if effect not in {e.value for e in PolicyEffect}:
                raise ValidationError(f"Unknown policy effect '{effect}'")
            policy.effect = effect
        policy.updated_by = updated_by
        policy = await self.repos.policies.update(policy)
        next_version = len(await self.repos.policy_versions.list_for_policy(tenant_id, policy_id)) + 1
        await self.repos.policy_versions.add(
            PolicyVersionModel(
                tenant_id=tenant_id, policy_id=policy_id, version_number=next_version,
                rules_snapshot=policy.rules, effect_snapshot=policy.effect, created_by=updated_by,
            )
        )
        return policy

    async def activate(self, tenant_id: str, policy_id: str) -> PolicyModel:
        policy = await self.repos.policies.get_or_404(policy_id)
        entity = _to_entity(policy)
        entity.activate()
        policy.status = entity.status.value
        return await self.repos.policies.update(policy)

    async def deprecate(self, tenant_id: str, policy_id: str) -> PolicyModel:
        policy = await self.repos.policies.get_or_404(policy_id)
        entity = _to_entity(policy)
        entity.deprecate()
        policy.status = entity.status.value
        return await self.repos.policies.update(policy)

    async def archive(self, tenant_id: str, policy_id: str) -> PolicyModel:
        policy = await self.repos.policies.get_or_404(policy_id)
        entity = _to_entity(policy)
        entity.archive()
        policy.status = entity.status.value
        return await self.repos.policies.update(policy)

    async def list_for_scope(self, tenant_id: str, scope: str, *, scope_ref_id: str | None = None) -> list[PolicyModel]:
        return await self.repos.policies.list_for_scope(tenant_id, scope, scope_ref_id=scope_ref_id)

    async def history(self, tenant_id: str, policy_id: str) -> list[PolicyVersionModel]:
        return await self.repos.policy_versions.list_for_policy(tenant_id, policy_id)
