"""VaultService: the Credential Vault. Secret material is always JSON-
serialized then Fernet-encrypted before it touches the database (see
`security/encryption.py`) — `CredentialModel.encrypted_payload` is
ciphertext, full stop, and `credential_metadata` is the only place
non-secret context (issuer, token endpoint, client_id) belongs, exactly
mirroring the Workflow Engine's `is_secret` variable design. Rotation
and expiry both go through the `Credential` domain entity's guarded
state machine — `rotate_credential` re-encrypts under a fresh Fernet
ciphertext even if the underlying secret material is unchanged, so a
credential's ciphertext doesn't sit static forever."""
from __future__ import annotations

import json
from datetime import datetime

from tool_platform.core.exceptions import ValidationError
from tool_platform.credentials.mappers import apply_credential_domain_to_model, credential_to_domain
from tool_platform.database.base import utcnow
from tool_platform.models.credential import CredentialModel, ToolCredentialBindingModel
from tool_platform.repositories.registry import RepositoryRegistry
from tool_platform.security.encryption import SecretsEncryptor, get_default_encryptor


class VaultService:
    def __init__(self, repos: RepositoryRegistry, *, encryptor: SecretsEncryptor | None = None):
        self.repos = repos
        self._encryptor = encryptor or get_default_encryptor()

    def _encrypt(self, secret_material: dict) -> str:
        return self._encryptor.encrypt(json.dumps(secret_material))

    def _decrypt(self, ciphertext: str) -> dict:
        return json.loads(self._encryptor.decrypt(ciphertext))

    async def create_credential(
        self, workspace_id: str, *, name: str, credential_type: str, secret_material: dict, owner_id: str,
        scopes: list[str] | None = None, expires_at: datetime | None = None, credential_metadata: dict | None = None,
    ) -> CredentialModel:
        return await self.repos.credentials.add(CredentialModel(
            workspace_id=workspace_id, name=name, credential_type=credential_type,
            encrypted_payload=self._encrypt(secret_material), scopes=scopes or [], owner_id=owner_id,
            expires_at=expires_at, credential_metadata=credential_metadata or {},
        ))

    async def get_secret(self, credential_id: str) -> dict:
        model = await self.repos.credentials.get_or_404(credential_id)
        if model.status == "revoked":
            raise ValidationError(f"credential '{credential_id}' has been revoked")
        if model.status == "expired":
            raise ValidationError(f"credential '{credential_id}' has expired")
        model.last_used_at = utcnow()
        await self.repos.credentials.update(model)
        return self._decrypt(model.encrypted_payload)

    async def list_for_workspace(self, workspace_id: str) -> list[CredentialModel]:
        return await self.repos.credentials.list_for_workspace(workspace_id)

    async def rotate_credential(
        self, credential_id: str, *, new_secret_material: dict, new_expires_at: datetime | None = None,
    ) -> CredentialModel:
        model = await self.repos.credentials.get_or_404(credential_id)
        entity = credential_to_domain(model)
        entity.begin_rotation()
        entity.complete_rotation(new_expires_at=new_expires_at)
        apply_credential_domain_to_model(entity, model)
        model.encrypted_payload = self._encrypt(new_secret_material)
        return await self.repos.credentials.update(model)

    async def revoke_credential(self, credential_id: str) -> CredentialModel:
        model = await self.repos.credentials.get_or_404(credential_id)
        entity = credential_to_domain(model)
        entity.revoke()
        apply_credential_domain_to_model(entity, model)
        return await self.repos.credentials.update(model)

    async def sweep_expirations(self, *, workspace_id: str | None = None, as_of: datetime | None = None) -> list[CredentialModel]:
        """Idempotent — safe to call on a timer. Returns credentials that
        this sweep call actually transitioned to EXPIRED (not ones already
        expired from a prior sweep)."""
        moment = as_of or utcnow()
        candidates = (
            await self.repos.credentials.list_for_workspace(workspace_id) if workspace_id
            else await self.repos.credentials.list_active_expiring_before(as_of=moment)
        )
        expired: list[CredentialModel] = []
        for model in candidates:
            entity = credential_to_domain(model)
            if entity.check_expiry(as_of=moment):
                apply_credential_domain_to_model(entity, model)
                await self.repos.credentials.update(model)
                expired.append(model)
        return expired

    # -- tool <-> credential binding --------------------------------------------

    async def bind_to_tool(self, tool_id: str, workspace_id: str, credential_id: str, *, is_default: bool = True) -> ToolCredentialBindingModel:
        await self.repos.credentials.get_or_404(credential_id)
        if is_default:
            existing_default = await self.repos.tool_credential_bindings.get_default_for_tool(tool_id, workspace_id)
            if existing_default is not None:
                existing_default.is_default = False
                await self.repos.tool_credential_bindings.update(existing_default)
        return await self.repos.tool_credential_bindings.add(ToolCredentialBindingModel(
            tool_id=tool_id, workspace_id=workspace_id, credential_id=credential_id, is_default=is_default,
        ))

    async def get_default_credential_for_tool(self, tool_id: str, workspace_id: str) -> CredentialModel | None:
        binding = await self.repos.tool_credential_bindings.get_default_for_tool(tool_id, workspace_id)
        if binding is None:
            return None
        return await self.repos.credentials.get_or_404(binding.credential_id)
