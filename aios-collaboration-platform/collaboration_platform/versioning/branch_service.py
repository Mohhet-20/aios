"""BranchService: named branches off an asset's version history,
backed by the guarded `Branch` domain entity for open/merged/closed."""
from __future__ import annotations

from collaboration_platform.core.exceptions import ConflictError
from collaboration_platform.domain.entities import Branch
from collaboration_platform.domain.enums import BranchStatus
from collaboration_platform.models.version import BranchModel
from collaboration_platform.repositories.registry import RepositoryRegistry


def branch_to_domain(model: BranchModel) -> Branch:
    return Branch(id=model.id, name=model.name, status=BranchStatus(model.status), closed_at=model.closed_at)


def apply_branch_domain(entity: Branch, model: BranchModel) -> None:
    model.status = entity.status.value
    model.closed_at = entity.closed_at


class BranchService:
    def __init__(self, repos: RepositoryRegistry):
        self.repos = repos

    async def create_branch(self, asset_id: str, *, name: str, created_by: str, base_version_id: str | None = None) -> BranchModel:
        await self.repos.assets.get_or_404(asset_id)
        if await self.repos.branches.get_by_name(asset_id, name) is not None:
            raise ConflictError(f"branch '{name}' already exists for asset '{asset_id}'")
        return await self.repos.branches.add(
            BranchModel(asset_id=asset_id, name=name, base_version_id=base_version_id, head_version_id=base_version_id, created_by=created_by)
        )

    async def update_head(self, branch_id: str, version_id: str) -> BranchModel:
        branch = await self.repos.branches.get_or_404(branch_id)
        branch.head_version_id = version_id
        return await self.repos.branches.update(branch)

    async def close(self, branch_id: str) -> BranchModel:
        branch = await self.repos.branches.get_or_404(branch_id)
        entity = branch_to_domain(branch)
        entity.close()
        apply_branch_domain(entity, branch)
        return await self.repos.branches.update(branch)

    async def list_for_asset(self, asset_id: str) -> list[BranchModel]:
        return await self.repos.branches.list_for_asset(asset_id)

    async def get_by_name(self, asset_id: str, name: str) -> BranchModel | None:
        return await self.repos.branches.get_by_name(asset_id, name)
