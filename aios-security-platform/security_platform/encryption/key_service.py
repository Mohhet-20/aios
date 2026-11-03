"""Encryption key lifecycle: get-or-create the tenant's active key,
and rotate it (retire the old key, mint a new active one). Rotation
does not retroactively re-encrypt existing `SecretVersionModel` rows —
each version keeps the `encryption_key_id` it was created with, so
past ciphertext stays decryptable while all *new* versions use the
freshly rotated key. This is the standard "rotate forward, don't
rewrite history" approach; a full re-encryption pass (decrypt every
version under the old key, re-encrypt under the new one) is a
deliberate non-goal here — it would need to be its own careful,
resumable batch job, not something rotate_key does inline."""
from __future__ import annotations

from security_platform.config.settings import Settings, get_settings
from security_platform.models.secrets import EncryptionKeyModel
from security_platform.repositories.registry import RepositoryRegistry
from security_platform.security.tokens import generate_raw_token


class EncryptionKeyService:
    def __init__(self, repos: RepositoryRegistry, *, settings: Settings | None = None):
        self.repos = repos
        self.settings = settings or get_settings()

    async def get_or_create_active_key(self, tenant_id: str) -> EncryptionKeyModel:
        existing = await self.repos.encryption_keys.get_active(tenant_id)
        if existing is not None:
            return existing
        key = EncryptionKeyModel(tenant_id=tenant_id, key_type="aes256-gcm", status="active", material_ref=generate_raw_token())
        return await self.repos.encryption_keys.add(key)

    async def rotate_key(self, tenant_id: str) -> EncryptionKeyModel:
        from security_platform.database.base import utcnow

        current = await self.repos.encryption_keys.get_active(tenant_id)
        if current is not None:
            current.status = "rotated"
            current.rotated_at = utcnow()
            await self.repos.encryption_keys.update(current)
        new_key = EncryptionKeyModel(tenant_id=tenant_id, key_type="aes256-gcm", status="active", material_ref=generate_raw_token())
        return await self.repos.encryption_keys.add(new_key)
