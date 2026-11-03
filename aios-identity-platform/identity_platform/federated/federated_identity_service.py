"""FederatedIdentityService: turns a validated `ExternalProfile` (from
`OAuth2Provider`/`SamlProvider`) into a platform `UserModel` + a linked
`ExternalIdentityModel`. Account-linking rule: an IdP-asserted email is
trusted as verified (that's what "federated identity" means), so a
first-time SSO login for an email that already has a platform account
links to that account rather than creating a duplicate; only when no
account exists at all does this provision a brand-new user, created
directly `ACTIVE` with `email_verified_at` set (unlike password
registration, there's no separate verification step to wait for)."""
from __future__ import annotations

from identity_platform.database.base import utcnow
from identity_platform.domain.enums import UserStatus
from identity_platform.federated.provider import ExternalProfile
from identity_platform.models.federated import ExternalIdentityModel
from identity_platform.models.user import UserModel
from identity_platform.repositories.registry import RepositoryRegistry


class FederatedIdentityService:
    def __init__(self, repos: RepositoryRegistry):
        self.repos = repos

    async def provision_or_login(self, profile: ExternalProfile) -> UserModel:
        existing_link = await self.repos.external_identities.get_by_provider_identity(
            profile.provider_key.value, profile.external_user_id
        )
        if existing_link is not None:
            return await self.repos.users.get_or_404(existing_link.user_id)

        user: UserModel | None = None
        if profile.email:
            user = await self.repos.users.get_by_email(profile.email)

        if user is None:
            user = UserModel(
                email=(profile.email or f"{profile.provider_key.value}:{profile.external_user_id}").lower(),
                status=UserStatus.ACTIVE.value, display_name=profile.display_name, email_verified_at=utcnow(),
            )
            await self.repos.users.add(user)

        await self.link_identity(user.id, profile)
        return user

    async def link_identity(self, user_id: str, profile: ExternalProfile) -> ExternalIdentityModel:
        return await self.repos.external_identities.add(ExternalIdentityModel(
            user_id=user_id, provider_key=profile.provider_key.value, provider_user_id=profile.external_user_id,
            provider_email=profile.email, raw_profile=profile.raw_profile,
        ))

    async def unlink_identity(self, external_identity_id: str) -> None:
        link = await self.repos.external_identities.get_or_404(external_identity_id)
        await self.repos.external_identities.delete(link, hard=True)

    async def list_linked_identities(self, user_id: str) -> list[ExternalIdentityModel]:
        return await self.repos.external_identities.list_for_user(user_id)
