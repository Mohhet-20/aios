"""AI Governance: a lightweight registry of governed assets (models,
prompts, workflows, datasets, agents, knowledge bases — see
`GovernanceAssetModel`'s "own the pointer, not the data" docstring)
plus lifecycle-stage tracking. Forward progression through the stage
order requires the *next* stage in sequence; DEPRECATED/RETIRED are
reachable as a "kill switch" from any earlier stage, since pulling an
asset out of service shouldn't require walking back through every
intermediate stage.

`register_asset` is idempotent-by-external-ref (check-if-registered,
then create if not) — a classic check-then-act sequence. Two
concurrent registrations of the same external asset could otherwise
both miss finding an existing row and both insert one, so the lookup
and the insert (including the commit) are serialized per
`tenant_id:asset_type:external_ref_id` with an in-process
`asyncio.Lock`, the same commit-spanning-lock pattern used throughout
the AIOS build."""
from __future__ import annotations

import asyncio
from collections import defaultdict

from security_platform.core.exceptions import ValidationError
from security_platform.domain.enums import GovernanceAssetType, LifecycleStage
from security_platform.models.governance import GovernanceAssetModel
from security_platform.repositories.registry import RepositoryRegistry

_STAGE_ORDER = [
    LifecycleStage.DRAFT, LifecycleStage.REVIEW, LifecycleStage.APPROVED,
    LifecycleStage.PRODUCTION, LifecycleStage.DEPRECATED, LifecycleStage.RETIRED,
]
_KILL_SWITCH_STAGES = {LifecycleStage.DEPRECATED.value, LifecycleStage.RETIRED.value}


class GovernanceAssetService:
    _registration_locks: dict[str, asyncio.Lock] = defaultdict(asyncio.Lock)

    def __init__(self, repos: RepositoryRegistry):
        self.repos = repos

    async def register_asset(
        self, tenant_id: str, *, asset_type: str, external_ref_id: str, name: str,
        owner_id: str | None = None, created_by: str | None = None,
    ) -> GovernanceAssetModel:
        if asset_type not in {t.value for t in GovernanceAssetType}:
            raise ValidationError(f"Unknown governance asset type '{asset_type}'")
        lock_key = f"{tenant_id}:{asset_type}:{external_ref_id}"
        async with self._registration_locks[lock_key]:
            existing = await self.repos.governance_assets.get_by_external_ref(tenant_id, asset_type, external_ref_id)
            if existing is not None:
                return existing
            asset = GovernanceAssetModel(
                tenant_id=tenant_id, asset_type=asset_type, external_ref_id=external_ref_id, name=name,
                owner_id=owner_id, lifecycle_stage=LifecycleStage.DRAFT.value, created_by=created_by,
            )
            asset = await self.repos.governance_assets.add(asset)
            await self.repos.session.commit()
            return asset

    async def set_owner(self, tenant_id: str, asset_id: str, owner_id: str) -> GovernanceAssetModel:
        asset = await self.repos.governance_assets.get_or_404(asset_id)
        asset.owner_id = owner_id
        return await self.repos.governance_assets.update(asset)

    async def advance_stage(self, tenant_id: str, asset_id: str, target_stage: str) -> GovernanceAssetModel:
        asset = await self.repos.governance_assets.get_or_404(asset_id)
        if target_stage not in {s.value for s in LifecycleStage}:
            raise ValidationError(f"Unknown lifecycle stage '{target_stage}'")
        current_index = _STAGE_ORDER.index(LifecycleStage(asset.lifecycle_stage))
        target_index = _STAGE_ORDER.index(LifecycleStage(target_stage))
        is_next_step = target_index == current_index + 1
        is_kill_switch = target_stage in _KILL_SWITCH_STAGES and target_index > current_index
        if not (is_next_step or is_kill_switch):
            raise ValidationError(f"Cannot advance governance asset '{asset_id}' from '{asset.lifecycle_stage}' to '{target_stage}'")
        asset.lifecycle_stage = target_stage
        return await self.repos.governance_assets.update(asset)

    async def list_by_stage(self, tenant_id: str, stage: str) -> list[GovernanceAssetModel]:
        return await self.repos.governance_assets.list_by_lifecycle_stage(tenant_id, stage)
