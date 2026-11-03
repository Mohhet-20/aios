"""ConflictService: detects when two active edit sessions on the same
asset have diverged (different `base_version_id`s, meaning at least
one of them is editing against a version that is no longer the
asset's current head) and records + resolves the resulting
`ConflictRecord`. Detection happens on-demand (called when a save is
attempted, or periodically) rather than via a background watcher,
since the only thing that actually needs to know about a conflict is
whoever is about to write."""
from __future__ import annotations

from collaboration_platform.core.exceptions import EditConflictError, NotFoundError
from collaboration_platform.database.base import utcnow
from collaboration_platform.domain.enums import ConflictResolutionStrategy
from collaboration_platform.models.presence import ConflictRecordModel
from collaboration_platform.repositories.registry import RepositoryRegistry


class ConflictService:
    def __init__(self, repos: RepositoryRegistry):
        self.repos = repos

    async def detect_conflicts(self, asset_id: str) -> list[ConflictRecordModel]:
        """Pairwise-compares every active edit session's base_version_id
        for this asset; any pair with different, non-null bases is a
        detected conflict (recorded once, not re-recorded if an
        unresolved record for the same pair already exists)."""
        sessions = await self.repos.edit_sessions.list_active_for_asset(asset_id)
        bases = [s for s in sessions if s.base_version_id is not None]
        existing_unresolved = await self.repos.conflict_records.list_for_asset(asset_id)
        existing_pairs = {
            frozenset((c.session_a_id, c.session_b_id)) for c in existing_unresolved if c.resolved_at is None
        }
        new_conflicts: list[ConflictRecordModel] = []
        for i in range(len(bases)):
            for j in range(i + 1, len(bases)):
                a, b = bases[i], bases[j]
                if a.base_version_id == b.base_version_id:
                    continue
                pair_key = frozenset((a.id, b.id))
                if pair_key in existing_pairs:
                    continue
                record = await self.repos.conflict_records.add(
                    ConflictRecordModel(asset_id=asset_id, session_a_id=a.id, session_b_id=b.id)
                )
                new_conflicts.append(record)
                existing_pairs.add(pair_key)
        return new_conflicts

    async def resolve(
        self, conflict_id: str, *, strategy: ConflictResolutionStrategy, resolved_by: str, notes: str | None = None
    ) -> ConflictRecordModel:
        conflict = await self.repos.conflict_records.get(conflict_id)
        if conflict is None:
            raise NotFoundError(f"conflict record '{conflict_id}' not found")
        if conflict.resolved_at is not None:
            raise EditConflictError(f"conflict '{conflict_id}' has already been resolved")
        conflict.resolution_strategy = strategy.value
        conflict.resolved_by = resolved_by
        conflict.resolved_at = utcnow()
        conflict.notes = notes
        return await self.repos.conflict_records.update(conflict)

    async def list_unresolved(self) -> list[ConflictRecordModel]:
        return await self.repos.conflict_records.list_unresolved()
