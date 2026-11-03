"""ComplianceService: organization-level compliance metadata
(`OrganizationModel.compliance_metadata` — data residency, applicable
frameworks, retention overrides) plus two concrete compliance
operations every enterprise identity platform needs: a subject-access
data export for a single user (GDPR/CCPA-style "what do you have on
me") and a lightweight compliance posture summary for an organization."""
from __future__ import annotations

from dataclasses import dataclass, field

from identity_platform.domain.enums import MfaFactorStatus
from identity_platform.repositories.registry import RepositoryRegistry


@dataclass
class UserDataExport:
    user_id: str
    profile: dict
    organization_memberships: list[dict] = field(default_factory=list)
    sessions: list[dict] = field(default_factory=list)
    login_history: list[dict] = field(default_factory=list)
    mfa_factors: list[dict] = field(default_factory=list)
    external_identities: list[dict] = field(default_factory=list)
    api_keys: list[dict] = field(default_factory=list)


class ComplianceService:
    def __init__(self, repos: RepositoryRegistry):
        self.repos = repos

    async def update_compliance_metadata(self, organization_id: str, *, metadata: dict) -> dict:
        org = await self.repos.organizations.get_or_404(organization_id)
        org.compliance_metadata = {**org.compliance_metadata, **metadata}
        await self.repos.organizations.update(org)
        return org.compliance_metadata

    async def export_user_data(self, user_id: str) -> UserDataExport:
        user = await self.repos.users.get_or_404(user_id)

        memberships = await self.repos.organization_memberships.list_for_user(user_id)
        sessions = await self.repos.sessions.list_active_for_user(user_id)
        history = await self.repos.login_history.list_for_user(user_id)
        factors = await self.repos.mfa_factors.list_for_user(user_id)
        identities = await self.repos.external_identities.list_for_user(user_id)
        keys = await self.repos.api_keys.list_for_owner("user", user_id)

        return UserDataExport(
            user_id=user_id,
            profile={
                "email": user.email, "display_name": user.display_name, "status": user.status,
                "created_at": str(user.created_at), "timezone": user.timezone, "locale": user.locale,
            },
            organization_memberships=[{"organization_id": m.organization_id, "status": m.status, "joined_at": str(m.joined_at)} for m in memberships],
            sessions=[{"id": s.id, "created_at": str(s.created_at), "ip_address": s.ip_address} for s in sessions],
            login_history=[{"success": h.success, "created_at": str(h.created_at), "ip_address": h.ip_address} for h in history],
            mfa_factors=[{"factor_type": f.factor_type, "status": f.status} for f in factors],
            external_identities=[{"provider_key": e.provider_key, "linked_at": str(e.linked_at)} for e in identities],
            api_keys=[{"id": k.id, "name": k.name, "status": k.status} for k in keys],
        )

    async def compliance_summary(self, organization_id: str) -> dict:
        members = await self.repos.organization_memberships.list_for_organization(organization_id)
        active_member_ids = [m.user_id for m in members if m.status == "active"]

        mfa_enabled_count = 0
        for user_id in active_member_ids:
            factors = await self.repos.mfa_factors.list_for_user(user_id)
            if any(f.status == MfaFactorStatus.ACTIVE.value for f in factors):
                mfa_enabled_count += 1

        policies = await self.repos.security_policies.list_for_organization(organization_id)

        return {
            "organization_id": organization_id,
            "active_member_count": len(active_member_ids),
            "mfa_enabled_member_count": mfa_enabled_count,
            "mfa_adoption_rate": round(mfa_enabled_count / len(active_member_ids), 4) if active_member_ids else 0.0,
            "active_security_policy_count": sum(1 for p in policies if p.is_active),
        }
