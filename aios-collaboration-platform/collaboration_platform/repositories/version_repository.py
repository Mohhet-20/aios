from __future__ import annotations

import json

from sqlalchemy import desc, func, select, text

from collaboration_platform.database.base import new_uuid, utcnow
from collaboration_platform.models.version import BranchModel, MergeModel, VersionModel
from collaboration_platform.repositories.base import SQLAlchemyRepository


class VersionRepository(SQLAlchemyRepository[VersionModel]):
    model = VersionModel

    async def list_for_asset(self, asset_id: str, *, branch_name: str | None = None) -> list[VersionModel]:
        stmt = select(VersionModel).where(VersionModel.asset_id == asset_id)
        if branch_name:
            stmt = stmt.where(VersionModel.branch_name == branch_name)
        stmt = stmt.order_by(desc(VersionModel.version_number))
        return list((await self.session.execute(stmt)).scalars().all())

    async def get_latest(self, asset_id: str, *, branch_name: str = "main") -> VersionModel | None:
        stmt = (
            select(VersionModel)
            .where(VersionModel.asset_id == asset_id, VersionModel.branch_name == branch_name)
            .order_by(desc(VersionModel.version_number))
            .limit(1)
        )
        return (await self.session.execute(stmt)).scalars().first()

    async def add_next_version(
        self, asset_id: str, branch_name: str, *, content_snapshot: dict, change_summary: str | None,
        is_release: bool, release_tag: str | None, created_by: str,
    ) -> VersionModel:
        """Computes the next `version_number` (and links `parent_version_id`
        to whatever the current highest-numbered version is) and inserts
        the new row, all as one `INSERT ... SELECT` statement. This
        exists because a separate "read max, then insert" — the original
        implementation — is a textbook TOCTOU race: proven by a stress
        test to raise `UNIQUE constraint failed` under real concurrent
        version creation for the same asset+branch. Collapsing the read
        and the write into a single statement means SQLite's per-statement
        write lock makes the whole read-then-decide-then-write atomic
        against other concurrent writers, the same principle as the
        Identity Platform's seat-quota fix — no application-level lock
        needed because this reduces cleanly to one statement."""
        new_id = new_uuid()
        created_at = utcnow()
        stmt = text("""
            INSERT INTO cp_versions (
                id, asset_id, branch_name, version_number, parent_version_id,
                content_snapshot, change_summary, is_release, release_tag, created_by, created_at
            )
            SELECT
                :new_id, :asset_id, :branch_name, COALESCE(MAX(version_number), 0) + 1,
                (SELECT v2.id FROM cp_versions v2
                 WHERE v2.asset_id = :asset_id AND v2.branch_name = :branch_name
                 ORDER BY v2.version_number DESC LIMIT 1),
                :content_snapshot, :change_summary, :is_release, :release_tag, :created_by, :created_at
            FROM cp_versions
            WHERE asset_id = :asset_id AND branch_name = :branch_name
        """)
        await self.session.execute(stmt, {
            "new_id": new_id, "asset_id": asset_id, "branch_name": branch_name,
            "content_snapshot": json.dumps(content_snapshot), "change_summary": change_summary,
            "is_release": is_release, "release_tag": release_tag, "created_by": created_by, "created_at": created_at,
        })
        await self.session.flush()
        return await self.get_or_404(new_id)

    async def next_version_number(self, asset_id: str, *, branch_name: str = "main") -> int:
        stmt = select(func.max(VersionModel.version_number)).where(
            VersionModel.asset_id == asset_id, VersionModel.branch_name == branch_name
        )
        current_max = (await self.session.execute(stmt)).scalar_one_or_none()
        return (current_max or 0) + 1

    async def list_releases(self, asset_id: str) -> list[VersionModel]:
        stmt = select(VersionModel).where(VersionModel.asset_id == asset_id, VersionModel.is_release.is_(True))
        return list((await self.session.execute(stmt)).scalars().all())


class BranchRepository(SQLAlchemyRepository[BranchModel]):
    model = BranchModel

    async def list_for_asset(self, asset_id: str) -> list[BranchModel]:
        stmt = select(BranchModel).where(BranchModel.asset_id == asset_id)
        return list((await self.session.execute(stmt)).scalars().all())

    async def get_by_name(self, asset_id: str, name: str) -> BranchModel | None:
        stmt = select(BranchModel).where(BranchModel.asset_id == asset_id, BranchModel.name == name)
        return (await self.session.execute(stmt)).scalars().first()


class MergeRepository(SQLAlchemyRepository[MergeModel]):
    model = MergeModel

    async def list_for_branch(self, branch_id: str) -> list[MergeModel]:
        stmt = select(MergeModel).where(MergeModel.branch_id == branch_id)
        return list((await self.session.execute(stmt)).scalars().all())
