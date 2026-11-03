"""ORM <-> domain-aggregate bridge for `OrganizationMembership` and
`Invitation`."""
from __future__ import annotations

from identity_platform.domain.entities import Invitation, OrganizationMembership, _aware
from identity_platform.domain.enums import InvitationStatus, MembershipStatus
from identity_platform.models.invitation import InvitationModel
from identity_platform.models.membership import OrganizationMembershipModel


def org_membership_to_domain(model: OrganizationMembershipModel) -> OrganizationMembership:
    return OrganizationMembership(
        id=model.id, organization_id=model.organization_id, user_id=model.user_id,
        status=MembershipStatus(model.status), removed_at=_aware(model.removed_at),
    )


def apply_org_membership_domain_to_model(entity: OrganizationMembership, model: OrganizationMembershipModel) -> None:
    model.status = entity.status.value
    model.removed_at = entity.removed_at


def invitation_to_domain(model: InvitationModel) -> Invitation:
    return Invitation(
        id=model.id, email=model.email, status=InvitationStatus(model.status),
        accepted_at=_aware(model.accepted_at), accepted_by_user_id=model.accepted_by_user_id,
        revoked_at=_aware(model.revoked_at),
    )


def apply_invitation_domain_to_model(entity: Invitation, model: InvitationModel) -> None:
    model.status = entity.status.value
    model.accepted_at = entity.accepted_at
    model.accepted_by_user_id = entity.accepted_by_user_id
    model.revoked_at = entity.revoked_at
