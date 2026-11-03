"""OrganizationService: the tenancy root. Creating an organization also
creates its owner's `OrganizationMembershipModel` and grants the
built-in `org_owner` role in the same call, so "an organization with no
owner" is never an observable state. Ownership transfer requires the
new owner to already be an active member — you can't hand ownership to
someone who isn't even in the organization."""
from __future__ import annotations

from slugify import slugify

from identity_platform.authorization.assignment_service import RoleAssignmentService
from identity_platform.config.settings import Settings, get_settings
from identity_platform.core.exceptions import ConflictError, MembershipError
from identity_platform.domain.enums import MembershipStatus, OrganizationStatus, PrincipalType, RoleScopeType
from identity_platform.models.membership import OrganizationMembershipModel
from identity_platform.models.organization import DepartmentModel, OrganizationModel
from identity_platform.repositories.registry import RepositoryRegistry


class OrganizationService:
    def __init__(self, repos: RepositoryRegistry, *, settings: Settings | None = None):
        self.repos = repos
        self.settings = settings or get_settings()

    async def create_organization(self, *, name: str, owner_user_id: str, slug: str | None = None) -> OrganizationModel:
        candidate_slug = slugify(slug or name)
        if await self.repos.organizations.get_by_slug(candidate_slug) is not None:
            raise ConflictError(f"organization slug '{candidate_slug}' is already taken")

        org = OrganizationModel(
            name=name, slug=candidate_slug, status=OrganizationStatus.ACTIVE.value, owner_user_id=owner_user_id,
            seat_quota=self.settings.default_org_seat_quota, workspace_quota=self.settings.default_org_workspace_quota,
        )
        await self.repos.organizations.add(org)

        await self.repos.organization_memberships.add(OrganizationMembershipModel(
            organization_id=org.id, user_id=owner_user_id, status=MembershipStatus.ACTIVE.value,
        ))

        owner_role = await self.repos.roles.get_by_slug(None, "org_owner")
        if owner_role is not None:
            await RoleAssignmentService(self.repos).assign_role(
                principal_type=PrincipalType.USER.value, principal_id=owner_user_id, role_id=owner_role.id,
                scope_type=RoleScopeType.ORGANIZATION, scope_id=org.id, granted_by=owner_user_id,
            )

        # An owner's first organisation becomes their primary one, so their sessions carry it from the start.
        owner = await self.repos.users.get(owner_user_id)
        if owner is not None and owner.primary_organization_id is None:
            owner.primary_organization_id = org.id
            await self.repos.users.update(owner)
        return org

    async def update_settings(self, org_id: str, *, settings: dict) -> OrganizationModel:
        org = await self.repos.organizations.get_or_404(org_id)
        org.settings = {**org.settings, **settings}
        return await self.repos.organizations.update(org)

    async def update_branding(self, org_id: str, *, branding: dict) -> OrganizationModel:
        org = await self.repos.organizations.get_or_404(org_id)
        org.branding = {**org.branding, **branding}
        return await self.repos.organizations.update(org)

    async def archive(self, org_id: str) -> OrganizationModel:
        org = await self.repos.organizations.get_or_404(org_id)
        org.status = OrganizationStatus.ARCHIVED.value
        return await self.repos.organizations.update(org)

    async def suspend(self, org_id: str) -> OrganizationModel:
        org = await self.repos.organizations.get_or_404(org_id)
        org.status = OrganizationStatus.SUSPENDED.value
        return await self.repos.organizations.update(org)

    async def reinstate(self, org_id: str) -> OrganizationModel:
        org = await self.repos.organizations.get_or_404(org_id)
        org.status = OrganizationStatus.ACTIVE.value
        return await self.repos.organizations.update(org)

    async def transfer_ownership(self, org_id: str, *, new_owner_user_id: str) -> OrganizationModel:
        org = await self.repos.organizations.get_or_404(org_id)
        membership = await self.repos.organization_memberships.get_for_org_and_user(org_id, new_owner_user_id)
        if membership is None or membership.status != MembershipStatus.ACTIVE.value:
            raise MembershipError(f"user '{new_owner_user_id}' must be an active member of '{org_id}' to receive ownership")

        org.owner_user_id = new_owner_user_id
        await self.repos.organizations.update(org)

        owner_role = await self.repos.roles.get_by_slug(None, "org_owner")
        if owner_role is not None:
            await RoleAssignmentService(self.repos).assign_role(
                principal_type=PrincipalType.USER.value, principal_id=new_owner_user_id, role_id=owner_role.id,
                scope_type=RoleScopeType.ORGANIZATION, scope_id=org.id, granted_by=org.owner_user_id or new_owner_user_id,
            )
        return org

    async def create_department(self, org_id: str, *, name: str, unit_type: str = "department", description: str | None = None, parent_department_id: str | None = None) -> DepartmentModel:
        await self.repos.organizations.get_or_404(org_id)
        return await self.repos.departments.add(DepartmentModel(
            organization_id=org_id, unit_type=unit_type, name=name, description=description,
            parent_department_id=parent_department_id,
        ))

    async def list_departments(self, org_id: str) -> list[DepartmentModel]:
        return await self.repos.departments.list_for_organization(org_id)
