import pytest

from identity_platform.core.exceptions import ConflictError, QuotaExceededError
from identity_platform.domain.enums import UserStatus
from identity_platform.models.user import UserModel
from identity_platform.organizations.group_service import GroupService
from identity_platform.organizations.membership_service import MembershipService
from identity_platform.organizations.organization_service import OrganizationService
from identity_platform.organizations.project_service import ProjectService
from identity_platform.organizations.team_service import TeamService
from identity_platform.organizations.workspace_service import WorkspaceService

pytestmark = pytest.mark.asyncio


async def _make_user(repos, db_session, email: str) -> UserModel:
    user = UserModel(email=email, status=UserStatus.ACTIVE.value)
    await repos.users.add(user)
    await db_session.commit()
    return user


async def _make_org(repos, db_session, name: str, owner_email: str):
    owner = await _make_user(repos, db_session, owner_email)
    org = await OrganizationService(repos).create_organization(name=name, owner_user_id=owner.id)
    await db_session.commit()
    return org, owner


async def test_create_workspace_team_project_hierarchy(repos, db_session):
    org, owner = await _make_org(repos, db_session, "Hierarchy Co", "hierarchy-owner@example.com")

    workspace = await WorkspaceService(repos).create_workspace(org.id, name="Main Workspace")
    await db_session.commit()
    assert workspace.slug == "main-workspace"

    team = await TeamService(repos).create_team(org.id, name="Platform Team", workspace_id=workspace.id)
    await db_session.commit()
    assert team.workspace_id == workspace.id

    project = await ProjectService(repos).create_project(workspace.id, name="Identity Project")
    await db_session.commit()
    assert project.workspace_id == workspace.id
    assert project.organization_id == org.id


async def test_workspace_slug_conflict(repos, db_session):
    org, _ = await _make_org(repos, db_session, "Slug Co", "slug-owner@example.com")
    service = WorkspaceService(repos)
    await service.create_workspace(org.id, name="Dup Workspace")
    await db_session.commit()

    with pytest.raises(ConflictError):
        await service.create_workspace(org.id, name="Dup Workspace")


async def test_workspace_quota_enforced(repos, db_session):
    org, _ = await _make_org(repos, db_session, "Quota Co", "quota-owner@example.com")
    org.workspace_quota = 1
    await repos.organizations.update(org)
    await db_session.commit()

    service = WorkspaceService(repos)
    await service.create_workspace(org.id, name="First WS")
    await db_session.commit()

    with pytest.raises(QuotaExceededError):
        await service.create_workspace(org.id, name="Second WS")


async def test_group_membership(repos, db_session):
    org, owner = await _make_org(repos, db_session, "Group Co", "group-owner@example.com")
    member = await _make_user(repos, db_session, "group-member@example.com")

    group_service = GroupService(repos)
    group = await group_service.create_group(org.id, name="Engineering Group")
    await db_session.commit()

    await group_service.add_member(group.id, member.id)
    await db_session.commit()

    members = await group_service.list_members(group.id)
    assert len(members) == 1
    assert members[0].user_id == member.id

    with pytest.raises(ConflictError):
        await group_service.add_member(group.id, member.id)

    await group_service.remove_member(group.id, member.id)
    await db_session.commit()
    assert await group_service.list_members(group.id) == []


async def test_organization_seat_quota_enforced(repos, db_session):
    org, owner = await _make_org(repos, db_session, "Seat Co", "seat-owner@example.com")
    org.seat_quota = 1  # owner already fills the one seat
    await repos.organizations.update(org)
    await db_session.commit()

    newcomer = await _make_user(repos, db_session, "seat-newcomer@example.com")
    membership_service = MembershipService(repos)
    with pytest.raises(QuotaExceededError):
        await membership_service.add_organization_member(org.id, newcomer.id)


async def test_workspace_team_project_membership_roundtrip(repos, db_session):
    org, owner = await _make_org(repos, db_session, "Membership Co", "membership-owner@example.com")
    workspace = await WorkspaceService(repos).create_workspace(org.id, name="WS")
    team = await TeamService(repos).create_team(org.id, name="Team", workspace_id=workspace.id)
    project = await ProjectService(repos).create_project(workspace.id, name="Proj")
    await db_session.commit()

    member = await _make_user(repos, db_session, "hierarchy-member@example.com")
    membership_service = MembershipService(repos)

    await membership_service.add_workspace_member(workspace.id, member.id)
    await membership_service.add_team_member(team.id, member.id)
    await membership_service.add_project_member(project.id, member.id)
    await db_session.commit()

    assert len(await membership_service.list_workspace_members(workspace.id)) == 1
    assert len(await membership_service.list_team_members(team.id)) == 1
    assert len(await membership_service.list_project_members(project.id)) == 1

    await membership_service.remove_workspace_member(workspace.id, member.id)
    await membership_service.remove_team_member(team.id, member.id)
    await membership_service.remove_project_member(project.id, member.id)
    await db_session.commit()

    assert await membership_service.list_workspace_members(workspace.id) == []
    assert await membership_service.list_team_members(team.id) == []
    assert await membership_service.list_project_members(project.id) == []
