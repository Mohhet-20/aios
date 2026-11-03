"""ShareLinkService / ExternalShareService: shareable links (a raw
token shown once, only its hash persisted — same pattern as every
raw-secret-shown-once flow in this platform, mirroring the Identity
Platform's `security/tokens.py`) and direct external-email invitations,
both scoped to a single asset and a single permission level."""
from __future__ import annotations

from datetime import timedelta

from collaboration_platform.config.settings import Settings, get_settings
from collaboration_platform.core.exceptions import (
    ExternalSharingDisabledError,
    NotFoundError,
    ShareLinkExpiredError,
    ShareLinkRevokedError,
)
from collaboration_platform.database.base import utcnow
from collaboration_platform.domain.enums import SharePermission
from collaboration_platform.models.governance import ExternalShareModel, SharingLinkModel
from collaboration_platform.repositories.registry import RepositoryRegistry
from collaboration_platform.security.tokens import generate_raw_token, hash_token


class ShareLinkService:
    def __init__(self, repos: RepositoryRegistry, *, settings: Settings | None = None):
        self.repos = repos
        self.settings = settings or get_settings()

    async def create_link(self, asset_id: str, *, created_by: str, permission: SharePermission = SharePermission.VIEW) -> tuple[SharingLinkModel, str]:
        await self.repos.assets.get_or_404(asset_id)
        raw_token = generate_raw_token(num_bytes=self.settings.sharing_link_token_bytes)
        link = await self.repos.sharing_links.add(SharingLinkModel(
            asset_id=asset_id, token_hash=hash_token(raw_token), permission=permission.value, created_by=created_by,
            expires_at=utcnow() + timedelta(days=self.settings.external_share_link_ttl_days),
        ))
        return link, raw_token

    async def resolve_link(self, raw_token: str) -> SharingLinkModel:
        link = await self.repos.sharing_links.get_by_token_hash(hash_token(raw_token))
        if link is None:
            raise NotFoundError("sharing link not found")
        if link.revoked_at is not None:
            raise ShareLinkRevokedError(f"sharing link '{link.id}' has been revoked")
        if link.expires_at is not None and link.expires_at < utcnow():
            raise ShareLinkExpiredError(f"sharing link '{link.id}' expired at {link.expires_at.isoformat()}")
        return link

    async def revoke_link(self, link_id: str) -> SharingLinkModel:
        link = await self.repos.sharing_links.get_or_404(link_id)
        link.revoked_at = utcnow()
        return await self.repos.sharing_links.update(link)

    async def list_for_asset(self, asset_id: str) -> list[SharingLinkModel]:
        return await self.repos.sharing_links.list_for_asset(asset_id)


class ExternalShareService:
    def __init__(self, repos: RepositoryRegistry, *, settings: Settings | None = None):
        self.repos = repos
        self.settings = settings or get_settings()

    async def invite(self, asset_id: str, email: str, *, invited_by: str, permission: SharePermission = SharePermission.VIEW, external_sharing_enabled: bool = True) -> ExternalShareModel:
        if not external_sharing_enabled:
            raise ExternalSharingDisabledError(f"external sharing is disabled for asset '{asset_id}'")
        await self.repos.assets.get_or_404(asset_id)
        existing = await self.repos.external_shares.get_for_asset_and_email(asset_id, email)
        if existing is not None and existing.revoked_at is None:
            return existing
        return await self.repos.external_shares.add(ExternalShareModel(asset_id=asset_id, email=email, permission=permission.value, invited_by=invited_by))

    async def accept(self, external_share_id: str) -> ExternalShareModel:
        share = await self.repos.external_shares.get_or_404(external_share_id)
        share.accepted_at = utcnow()
        return await self.repos.external_shares.update(share)

    async def revoke(self, external_share_id: str) -> ExternalShareModel:
        share = await self.repos.external_shares.get_or_404(external_share_id)
        share.revoked_at = utcnow()
        return await self.repos.external_shares.update(share)

    async def list_for_asset(self, asset_id: str) -> list[ExternalShareModel]:
        return await self.repos.external_shares.list_for_asset(asset_id)
