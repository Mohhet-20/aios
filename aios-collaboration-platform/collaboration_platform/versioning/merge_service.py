"""MergeService: merges a branch's head version into a target branch.
Honest disclosed limitation, the same category as the Tool Platform's
undocumented-connector gaps: this platform has no general-purpose
structural merge algorithm for arbitrary JSON content (that would
require understanding each owning platform's own schema). All three
declared strategies therefore resolve to "the target branch's new
head becomes the source branch's head content" — `FAST_FORWARD` and
`THREE_WAY` both take that path automatically (the distinction is
recorded for audit/reporting, not behaviorally different here), and
`MANUAL` requires the caller to supply the already-reconciled content
explicitly rather than have this service guess at a merge."""
from __future__ import annotations

from collaboration_platform.core.exceptions import BranchError, MergeConflictError
from collaboration_platform.domain.enums import BranchStatus, MergeStrategy
from collaboration_platform.models.version import MergeModel
from collaboration_platform.repositories.registry import RepositoryRegistry
from collaboration_platform.versioning.branch_service import BranchService, apply_branch_domain, branch_to_domain
from collaboration_platform.versioning.version_service import VersionService


class MergeService:
    def __init__(self, repos: RepositoryRegistry):
        self.repos = repos
        self.branches = BranchService(repos)
        self.versions = VersionService(repos)

    async def merge(
        self, branch_id: str, *, target_branch_name: str, merged_by: str, strategy: MergeStrategy = MergeStrategy.FAST_FORWARD,
        manual_content: dict | None = None,
    ) -> MergeModel:
        branch = await self.repos.branches.get_or_404(branch_id)
        if branch.status != BranchStatus.OPEN.value:
            raise BranchError(f"branch '{branch.name}' is not open (status={branch.status})")
        if branch.head_version_id is None:
            raise BranchError(f"branch '{branch.name}' has no commits to merge")

        if strategy == MergeStrategy.MANUAL:
            if manual_content is None:
                raise MergeConflictError("MANUAL merge strategy requires the caller to supply reconciled `manual_content`")
            content = manual_content
        else:
            head = await self.repos.versions.get_or_404(branch.head_version_id)
            content = dict(head.content_snapshot)

        merged_version = await self.versions.create_version(
            branch.asset_id, merged_by, content, branch_name=target_branch_name,
            change_summary=f"Merged branch '{branch.name}' ({strategy.value})",
        )

        merge_record = await self.repos.merges.add(MergeModel(
            branch_id=branch.id, target_branch_name=target_branch_name, merged_version_id=merged_version.id,
            strategy=strategy.value, merged_by=merged_by,
        ))

        entity = branch_to_domain(branch)
        entity.mark_merged()
        apply_branch_domain(entity, branch)
        await self.repos.branches.update(branch)

        return merge_record

    async def list_for_branch(self, branch_id: str) -> list[MergeModel]:
        return await self.repos.merges.list_for_branch(branch_id)
