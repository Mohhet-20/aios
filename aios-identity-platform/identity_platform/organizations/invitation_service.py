"""InvitationService: email-addressed, token-based invitations to join
an organization (optionally into a specific workspace, with a role
pre-selected). Acceptance is one atomic operation: consume the token,
create the org membership (and workspace membership, if the invite
named one), and assign the pre-selected role — all via the same
`RepositoryRegistry` session, so a partially-accepted invitation is
never observable."""
from __future__ import annotations

from datetime import timedelta

from identity_platform.authorization.assignment_service import RoleAssignmentService
from identity_platform.config.settings import Settings, get_settings
from identity_platform.core.exceptions import ConflictError, TokenAlreadyUsedError, TokenExpiredError
from identity_platform.database.base import utcnow
from identity_platform.domain.entities import _aware
from identity_platform.domain.enums import InvitationStatus, PrincipalType, RoleScopeType
from identity_platform.models.invitation import InvitationModel
from identity_platform.models.user import UserModel
from identity_platform.organizations.mappers import apply_invitation_domain_to_model, invitation_to_domain
from identity_platform.organizations.membership_service import MembershipService
from identity_platform.repositories.registry import RepositoryRegistry
from identity_platform.security.tokens import generate_raw_token, hash_token


class InvitationService:
    def __init__(self, repos: RepositoryRegistry, *, settings: Settings | None = None):
        self.repos = repos
        self.settings = settings or get_settings()
        self.membership_service = MembershipService(repos)

    async def create_invitation(
        self, org_id: str, *, email: str, invited_by: str, role_id: str | None = None, workspace_id: str | None = None,
    ) -> tuple[InvitationModel, str]:
        await self.repos.organizations.get_or_404(org_id)
        normalized_email = email.lower().strip()

        existing = await self.repos.invitations.get_pending_for_email(org_id, normalized_email)
        if existing is not None:
            raise ConflictError(f"a pending invitation already exists for '{normalized_email}' in this organization")

        raw_token = generate_raw_token()
        invitation = InvitationModel(
            organization_id=org_id, workspace_id=workspace_id, email=normalized_email, role_id=role_id,
            status=InvitationStatus.PENDING.value, token_hash=hash_token(raw_token), invited_by=invited_by,
            expires_at=utcnow() + timedelta(days=self.settings.invitation_ttl_days),
        )
        await self.repos.invitations.add(invitation)
        return invitation, raw_token

    async def accept_invitation(self, raw_token: str, *, user: UserModel) -> InvitationModel:
        invitation = await self.repos.invitations.get_by_token_hash(hash_token(raw_token))
        if invitation is None:
            raise TokenExpiredError("invitation token is invalid or has expired")
        if invitation.status == InvitationStatus.ACCEPTED.value:
            raise TokenAlreadyUsedError("invitation has already been accepted")
        if invitation.status in (InvitationStatus.REVOKED.value, InvitationStatus.EXPIRED.value):
            raise TokenExpiredError(f"invitation has been {invitation.status}")
        if _aware(invitation.expires_at) < utcnow():
            entity = invitation_to_domain(invitation)
            entity.expire()
            apply_invitation_domain_to_model(entity, invitation)
            await self.repos.invitations.update(invitation)
            raise TokenExpiredError("invitation has expired")

        await self.membership_service.add_organization_member(invitation.organization_id, user.id, invited_by=invitation.invited_by)
        if invitation.workspace_id:
            await self.membership_service.add_workspace_member(invitation.workspace_id, user.id)
        if invitation.role_id:
            role = await self.repos.roles.get_or_404(invitation.role_id)
            scope_id = invitation.workspace_id if role.scope_type == RoleScopeType.WORKSPACE.value else invitation.organization_id
            await RoleAssignmentService(self.repos).assign_role(
                principal_type=PrincipalType.USER.value, principal_id=user.id, role_id=invitation.role_id,
                scope_type=RoleScopeType(role.scope_type), scope_id=scope_id, granted_by=invitation.invited_by,
            )

        entity = invitation_to_domain(invitation)
        entity.accept(user_id=user.id)
        apply_invitation_domain_to_model(entity, invitation)
        return await self.repos.invitations.update(invitation)

    async def revoke_invitation(self, invitation_id: str) -> InvitationModel:
        invitation = await self.repos.invitations.get_or_404(invitation_id)
        entity = invitation_to_domain(invitation)
        entity.revoke()
        apply_invitation_domain_to_model(entity, invitation)
        return await self.repos.invitations.update(invitation)

    async def list_pending_for_organization(self, org_id: str) -> list[InvitationModel]:
        return await self.repos.invitations.list_for_organization(org_id, status=InvitationStatus.PENDING.value)
