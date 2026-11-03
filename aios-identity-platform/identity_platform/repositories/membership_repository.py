from __future__ import annotations

from sqlalchemy import select, text

from identity_platform.database.base import new_uuid, utcnow
from identity_platform.domain.enums import MembershipStatus
from identity_platform.models.membership import (
    GroupMembershipModel,
    OrganizationMembershipModel,
    ProjectMembershipModel,
    TeamMembershipModel,
    WorkspaceMembershipModel,
)
from identity_platform.repositories.base import SQLAlchemyRepository


class OrganizationMembershipRepository(SQLAlchemyRepository[OrganizationMembershipModel]):
    model = OrganizationMembershipModel

    async def get_for_org_and_user(self, organization_id: str, user_id: str) -> OrganizationMembershipModel | None:
        stmt = select(OrganizationMembershipModel).where(
            OrganizationMembershipModel.organization_id == organization_id, OrganizationMembershipModel.user_id == user_id,
        )
        return (await self.session.execute(stmt)).scalars().first()

    async def list_for_organization(self, organization_id: str, *, status: str | None = None) -> list[OrganizationMembershipModel]:
        stmt = select(OrganizationMembershipModel).where(OrganizationMembershipModel.organization_id == organization_id)
        if status:
            stmt = stmt.where(OrganizationMembershipModel.status == status)
        return list((await self.session.execute(stmt)).scalars().all())

    async def list_for_user(self, user_id: str) -> list[OrganizationMembershipModel]:
        stmt = select(OrganizationMembershipModel).where(OrganizationMembershipModel.user_id == user_id, OrganizationMembershipModel.status == "active")
        return list((await self.session.execute(stmt)).scalars().all())

    async def add_if_under_seat_quota(
        self, organization_id: str, user_id: str, *, invited_by: str | None = None,
    ) -> OrganizationMembershipModel | None:
        """Atomic, single-statement "insert only if there's still room"
        — `INSERT ... SELECT ... WHERE <count of active members> <
        <organization's seat_quota>` is one SQL statement, so SQLite's
        own locking guarantees no other writer can slip a row in
        between the count and the insert the way two separate
        statements (`SELECT` then `INSERT`) can under real concurrency
        (proven by `tests/performance/test_concurrency.py`, which
        oversold a naive check-then-insert by more than double under
        real parallel writers). Returns the new row, or None if the
        quota was already full — the caller raises `QuotaExceededError`
        in that case."""
        new_id = new_uuid()
        joined_at = utcnow()
        stmt = text("""
            INSERT INTO ip_organization_memberships (id, organization_id, user_id, status, invited_by, joined_at, removed_at)
            SELECT :new_id, :organization_id, :user_id, :status, :invited_by, :joined_at, NULL
            WHERE (
                SELECT COUNT(*) FROM ip_organization_memberships
                WHERE organization_id = :organization_id AND status = :active_status
            ) < (
                SELECT seat_quota FROM ip_organizations WHERE id = :organization_id
            )
        """)
        result = await self.session.execute(stmt, {
            "new_id": new_id, "organization_id": organization_id, "user_id": user_id,
            "status": MembershipStatus.ACTIVE.value, "active_status": MembershipStatus.ACTIVE.value,
            "invited_by": invited_by, "joined_at": joined_at,
        })
        if result.rowcount == 0:
            return None
        await self.session.flush()
        return await self.get(new_id)


class WorkspaceMembershipRepository(SQLAlchemyRepository[WorkspaceMembershipModel]):
    model = WorkspaceMembershipModel

    async def get_for_workspace_and_user(self, workspace_id: str, user_id: str) -> WorkspaceMembershipModel | None:
        stmt = select(WorkspaceMembershipModel).where(
            WorkspaceMembershipModel.workspace_id == workspace_id, WorkspaceMembershipModel.user_id == user_id,
        )
        return (await self.session.execute(stmt)).scalars().first()

    async def list_for_workspace(self, workspace_id: str) -> list[WorkspaceMembershipModel]:
        stmt = select(WorkspaceMembershipModel).where(WorkspaceMembershipModel.workspace_id == workspace_id)
        return list((await self.session.execute(stmt)).scalars().all())


class TeamMembershipRepository(SQLAlchemyRepository[TeamMembershipModel]):
    model = TeamMembershipModel

    async def list_for_team(self, team_id: str) -> list[TeamMembershipModel]:
        stmt = select(TeamMembershipModel).where(TeamMembershipModel.team_id == team_id)
        return list((await self.session.execute(stmt)).scalars().all())


class ProjectMembershipRepository(SQLAlchemyRepository[ProjectMembershipModel]):
    model = ProjectMembershipModel

    async def list_for_project(self, project_id: str) -> list[ProjectMembershipModel]:
        stmt = select(ProjectMembershipModel).where(ProjectMembershipModel.project_id == project_id)
        return list((await self.session.execute(stmt)).scalars().all())


class GroupMembershipRepository(SQLAlchemyRepository[GroupMembershipModel]):
    model = GroupMembershipModel

    async def list_for_group(self, group_id: str) -> list[GroupMembershipModel]:
        stmt = select(GroupMembershipModel).where(GroupMembershipModel.group_id == group_id)
        return list((await self.session.execute(stmt)).scalars().all())

    async def list_for_user(self, user_id: str) -> list[GroupMembershipModel]:
        stmt = select(GroupMembershipModel).where(GroupMembershipModel.user_id == user_id)
        return list((await self.session.execute(stmt)).scalars().all())
