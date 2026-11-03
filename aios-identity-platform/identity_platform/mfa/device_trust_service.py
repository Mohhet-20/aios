"""DeviceTrustService: "remember this device" — a trusted device lets a
user skip a fresh MFA challenge on subsequent logins until the trust
token's `expires_at`, scoped to `trusted_device_ttl_days`. The token is
hashed at rest like every other bearer credential in this platform."""
from __future__ import annotations

from datetime import timedelta

from identity_platform.config.settings import Settings, get_settings
from identity_platform.database.base import utcnow
from identity_platform.domain.entities import _aware
from identity_platform.models.mfa import TrustedDeviceModel
from identity_platform.repositories.registry import RepositoryRegistry
from identity_platform.security.tokens import generate_raw_token, hash_token


class DeviceTrustService:
    def __init__(self, repos: RepositoryRegistry, *, settings: Settings | None = None):
        self.repos = repos
        self.settings = settings or get_settings()

    async def trust_device(
        self, user_id: str, *, device_fingerprint: str, device_name: str | None = None,
        ip_address: str | None = None, user_agent: str | None = None,
    ) -> str:
        raw_token = generate_raw_token()
        await self.repos.trusted_devices.add(TrustedDeviceModel(
            user_id=user_id, device_fingerprint=device_fingerprint, device_name=device_name,
            token_hash=hash_token(raw_token), ip_address=ip_address, user_agent=user_agent,
            expires_at=utcnow() + timedelta(days=self.settings.trusted_device_ttl_days),
        ))
        return raw_token

    async def is_trusted(self, user_id: str, raw_token: str) -> bool:
        device = await self.repos.trusted_devices.get_by_token_hash(hash_token(raw_token))
        if device is None or device.user_id != user_id:
            return False
        if _aware(device.expires_at) < utcnow():
            return False
        device.last_seen_at = utcnow()
        await self.repos.trusted_devices.update(device)
        return True

    async def list_for_user(self, user_id: str) -> list[TrustedDeviceModel]:
        return await self.repos.trusted_devices.list_for_user(user_id)

    async def revoke(self, device_id: str) -> None:
        device = await self.repos.trusted_devices.get_or_404(device_id)
        await self.repos.trusted_devices.delete(device, hard=True)
