"""Credential Vault: secret CRUD, versioning (every rotation creates a
new encrypted version rather than overwriting one), and read access
that enforces `SecretAccessPolicyModel` and logs every attempt —
granted or denied — to `SecretAccessLogModel`. Encryption itself is
delegated to `encryption/envelope.py`; this service never handles raw
key material, only ciphertext/nonce pairs and the key reference used
to produce them.

`rotate_secret` reads the current active version, deactivates it,
creates a new one, and updates the secret's version counter/status —
a check-then-act sequence spanning multiple statements. Two concurrent
rotations of the same secret could otherwise both read the same
"current" active version and both mint a version claiming to be next,
so the whole sequence (including the commit) is serialized per
secret_id with an in-process `asyncio.Lock`, the same commit-spanning-
lock pattern used throughout the AIOS build (most recently the
Observability Platform's `AlertEvaluationService.fire_or_update`)."""
from __future__ import annotations

import asyncio
from collections import defaultdict

from security_platform.config.settings import Settings, get_settings
from security_platform.core.exceptions import SecretAccessDeniedError, SecretExpiredError, SecretNotFoundError
from security_platform.database.base import utcnow
from security_platform.domain.entities import _aware
from security_platform.domain.entities import Secret as SecretEntity
from security_platform.domain.enums import SecretStatus
from security_platform.encryption.envelope import decrypt, encrypt
from security_platform.encryption.key_service import EncryptionKeyService
from security_platform.models.secrets import SecretAccessLogModel, SecretModel, SecretVersionModel
from security_platform.repositories.registry import RepositoryRegistry


def _to_entity(model: SecretModel) -> SecretEntity:
    return SecretEntity(id=model.id, status=SecretStatus(model.status))


class SecretService:
    _rotation_locks: dict[str, asyncio.Lock] = defaultdict(asyncio.Lock)

    def __init__(self, repos: RepositoryRegistry, *, settings: Settings | None = None):
        self.repos = repos
        self.settings = settings or get_settings()
        self.keys = EncryptionKeyService(repos, settings=self.settings)

    async def _get_or_404(self, tenant_id: str, secret_id: str) -> SecretModel:
        secret = await self.repos.secrets.get(secret_id)
        if secret is None or secret.tenant_id != tenant_id:
            raise SecretNotFoundError(f"Secret '{secret_id}' not found")
        return secret

    async def create_secret(
        self, tenant_id: str, *, name: str, secret_type: str, plaintext_value: str,
        owner_id: str | None = None, description: str | None = None, expires_at=None, created_by: str | None = None,
    ) -> SecretModel:
        key = await self.keys.get_or_create_active_key(tenant_id)
        secret = await self.repos.secrets.add(
            SecretModel(
                tenant_id=tenant_id, name=name, secret_type=secret_type, status=SecretStatus.ACTIVE.value,
                owner_id=owner_id, description=description, current_version_number=1, expires_at=expires_at,
                created_by=created_by,
            )
        )
        ciphertext, nonce = encrypt(plaintext_value, master_key=self.settings.master_encryption_key, key_ref=key.material_ref)
        await self.repos.secret_versions.add(
            SecretVersionModel(
                tenant_id=tenant_id, secret_id=secret.id, version_number=1, ciphertext=ciphertext, nonce=nonce,
                encryption_key_id=key.id, is_active=True, created_by=created_by,
            )
        )
        return secret

    async def rotate_secret(self, tenant_id: str, secret_id: str, new_plaintext_value: str, *, rotated_by: str | None = None) -> SecretModel:
        async with self._rotation_locks[secret_id]:
            secret = await self._get_or_404(tenant_id, secret_id)
            entity = _to_entity(secret)
            entity.start_rotation()
            secret.status = entity.status.value
            await self.repos.secrets.update(secret)

            previous_active = await self.repos.secret_versions.get_active(tenant_id, secret_id)
            if previous_active is not None:
                previous_active.is_active = False
                await self.repos.secret_versions.update(previous_active)

            key = await self.keys.get_or_create_active_key(tenant_id)
            ciphertext, nonce = encrypt(new_plaintext_value, master_key=self.settings.master_encryption_key, key_ref=key.material_ref)
            next_version_number = secret.current_version_number + 1
            await self.repos.secret_versions.add(
                SecretVersionModel(
                    tenant_id=tenant_id, secret_id=secret_id, version_number=next_version_number, ciphertext=ciphertext,
                    nonce=nonce, encryption_key_id=key.id, is_active=True, created_by=rotated_by,
                )
            )
            secret.current_version_number = next_version_number

            entity = _to_entity(secret)
            entity.complete_rotation()
            secret.status = entity.status.value
            secret = await self.repos.secrets.update(secret)

            all_versions = await self.repos.secret_versions.list_for_secret(tenant_id, secret_id)
            retain = self.settings.secret_version_retention_count
            if len(all_versions) > retain:
                for stale in sorted(all_versions, key=lambda v: v.version_number)[: len(all_versions) - retain]:
                    await self.repos.secret_versions.delete(stale, hard=True)
            await self.repos.session.commit()
            return secret

    async def revoke_secret(self, tenant_id: str, secret_id: str) -> SecretModel:
        secret = await self._get_or_404(tenant_id, secret_id)
        entity = _to_entity(secret)
        entity.revoke()
        secret.status = entity.status.value
        return await self.repos.secrets.update(secret)

    async def expire_secret(self, tenant_id: str, secret_id: str) -> SecretModel:
        secret = await self._get_or_404(tenant_id, secret_id)
        entity = _to_entity(secret)
        entity.expire()
        secret.status = entity.status.value
        return await self.repos.secrets.update(secret)

    async def renew_secret(self, tenant_id: str, secret_id: str, *, extend_expires_at=None) -> SecretModel:
        secret = await self._get_or_404(tenant_id, secret_id)
        entity = _to_entity(secret)
        entity.renew()
        secret.status = entity.status.value
        if extend_expires_at is not None:
            secret.expires_at = extend_expires_at
        return await self.repos.secrets.update(secret)

    async def get_secret_value(self, tenant_id: str, secret_id: str, principal_id: str) -> str:
        secret = await self._get_or_404(tenant_id, secret_id)

        if secret.status == SecretStatus.REVOKED.value:
            await self._log_access(tenant_id, secret_id, principal_id, "read", success=False, reason="secret is revoked")
            raise SecretAccessDeniedError(f"Secret '{secret_id}' has been revoked")
        if secret.status == SecretStatus.EXPIRED.value:
            await self._log_access(tenant_id, secret_id, principal_id, "read", success=False, reason="secret is expired")
            raise SecretExpiredError(f"Secret '{secret_id}' has expired")

        policy = await self.repos.secret_access_policies.get_for_principal(tenant_id, secret_id, principal_id)
        if policy is None or not policy.can_read:
            await self._log_access(tenant_id, secret_id, principal_id, "read", success=False, reason="no read access policy")
            raise SecretAccessDeniedError(f"Principal '{principal_id}' cannot read secret '{secret_id}'")
        if policy.expires_at is not None and _aware(policy.expires_at) <= utcnow():
            await self._log_access(tenant_id, secret_id, principal_id, "read", success=False, reason="access policy expired")
            raise SecretAccessDeniedError(f"Access policy for principal '{principal_id}' on secret '{secret_id}' has expired")

        active_version = await self.repos.secret_versions.get_active(tenant_id, secret_id)
        if active_version is None:
            await self._log_access(tenant_id, secret_id, principal_id, "read", success=False, reason="no active version")
            raise SecretNotFoundError(f"Secret '{secret_id}' has no active version")

        key = await self.repos.encryption_keys.get(active_version.encryption_key_id)
        plaintext = decrypt(
            active_version.ciphertext, active_version.nonce, master_key=self.settings.master_encryption_key, key_ref=key.material_ref
        )
        await self._log_access(tenant_id, secret_id, principal_id, "read", success=True)
        return plaintext

    async def inject_for_environment(self, tenant_id: str, secret_names: list[str], principal_id: str) -> dict[str, str]:
        """Environment Secret Injection: resolve a batch of secrets by
        name into a plaintext env-var-style mapping, honoring the same
        access-policy checks and audit logging as a single read."""
        env: dict[str, str] = {}
        for name in secret_names:
            secret = await self.repos.secrets.get_by_name(tenant_id, name)
            if secret is None:
                raise SecretNotFoundError(f"Secret named '{name}' not found")
            env[name] = await self.get_secret_value(tenant_id, secret.id, principal_id)
        return env

    async def _log_access(self, tenant_id: str, secret_id: str, principal_id: str, action: str, *, success: bool, reason: str | None = None) -> None:
        await self.repos.secret_access_log.add(
            SecretAccessLogModel(tenant_id=tenant_id, secret_id=secret_id, principal_id=principal_id, action=action, success=success, reason=reason)
        )
