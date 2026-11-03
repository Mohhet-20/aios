"""ApiKeyService: issues scoped, hashed-at-rest API keys owned by a
user or service account. The raw key is only ever returned once, at
issuance/rotation; `key_prefix` (a non-secret leading slice of the raw
key) is what a "your API keys" list UI shows so an owner can recognize
`sk_a1b2c3d4...` without the platform ever storing or re-displaying
the full secret."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import timedelta

from identity_platform.authorization.registry import PERMISSION_KEYS, WILDCARD_ALL
from identity_platform.config.settings import Settings, get_settings
from identity_platform.core.exceptions import ApiKeyExpiredError, ApiKeyRevokedError, UnknownPermissionError
from identity_platform.database.base import utcnow
from identity_platform.domain.entities import _aware
from identity_platform.domain.enums import ApiKeyStatus
from identity_platform.api_keys.mappers import api_key_to_domain, apply_api_key_domain_to_model
from identity_platform.models.api_key import ApiKeyModel
from identity_platform.repositories.registry import RepositoryRegistry
from identity_platform.security.tokens import generate_raw_token, hash_token


def _validate_scopes(scopes: list[str]) -> None:
    for scope in scopes:
        if scope == WILDCARD_ALL or scope.endswith(":manage"):
            continue
        if scope not in PERMISSION_KEYS:
            raise UnknownPermissionError(f"'{scope}' is not a registered permission")


@dataclass
class ApiKeyIssueResult:
    api_key: ApiKeyModel
    raw_key: str


class ApiKeyService:
    def __init__(self, repos: RepositoryRegistry, *, settings: Settings | None = None):
        self.repos = repos
        self.settings = settings or get_settings()

    async def issue_key(
        self, organization_id: str, *, owner_type: str, owner_id: str, name: str, created_by: str,
        scopes: list[str] | None = None, workspace_id: str | None = None, expires_at=None,
    ) -> ApiKeyIssueResult:
        await self.repos.organizations.get_or_404(organization_id)
        scopes = scopes or []
        _validate_scopes(scopes)

        if expires_at is None and self.settings.api_key_default_ttl_days is not None:
            expires_at = utcnow() + timedelta(days=self.settings.api_key_default_ttl_days)

        raw_key = generate_raw_token()
        key_prefix = raw_key[: self.settings.api_key_prefix_length]

        api_key = ApiKeyModel(
            organization_id=organization_id, workspace_id=workspace_id, owner_type=owner_type, owner_id=owner_id,
            name=name, key_prefix=key_prefix, key_hash=hash_token(raw_key), scopes=scopes,
            status=ApiKeyStatus.ACTIVE.value, created_by=created_by, expires_at=expires_at,
        )
        await self.repos.api_keys.add(api_key)
        return ApiKeyIssueResult(api_key=api_key, raw_key=raw_key)

    async def verify_key(self, raw_key: str) -> ApiKeyModel:
        api_key = await self.repos.api_keys.get_by_key_hash(hash_token(raw_key))
        if api_key is None:
            raise ApiKeyRevokedError("API key is invalid")
        if api_key.status == ApiKeyStatus.REVOKED.value:
            raise ApiKeyRevokedError(f"API key '{api_key.id}' has been revoked")
        if api_key.status == ApiKeyStatus.EXPIRED.value or (api_key.expires_at is not None and _aware(api_key.expires_at) < utcnow()):
            if api_key.status != ApiKeyStatus.EXPIRED.value:
                entity = api_key_to_domain(api_key)
                entity.expire()
                apply_api_key_domain_to_model(entity, api_key)
                await self.repos.api_keys.update(api_key)
            raise ApiKeyExpiredError(f"API key '{api_key.id}' has expired")

        api_key.last_used_at = utcnow()
        await self.repos.api_keys.update(api_key)
        return api_key

    async def revoke_key(self, api_key_id: str, *, reason: str = "manual_revocation") -> ApiKeyModel:
        api_key = await self.repos.api_keys.get_or_404(api_key_id)
        entity = api_key_to_domain(api_key)
        entity.revoke(reason=reason)
        apply_api_key_domain_to_model(entity, api_key)
        return await self.repos.api_keys.update(api_key)

    async def rotate_key(self, api_key_id: str) -> ApiKeyIssueResult:
        """Revokes the old key and issues a fresh one with identical
        scopes/owner — the old raw key stops working the instant this
        returns, so a caller must swap to the new one immediately."""
        old = await self.repos.api_keys.get_or_404(api_key_id)
        await self.revoke_key(api_key_id, reason="rotated")
        return await self.issue_key(
            old.organization_id, owner_type=old.owner_type, owner_id=old.owner_id, name=old.name,
            created_by=old.created_by, scopes=list(old.scopes), workspace_id=old.workspace_id,
        )

    async def list_for_owner(self, owner_type: str, owner_id: str) -> list[ApiKeyModel]:
        return await self.repos.api_keys.list_for_owner(owner_type, owner_id)

    async def sweep_expirations(self) -> list[ApiKeyModel]:
        expired: list[ApiKeyModel] = []
        for api_key in await self.repos.api_keys.list_expired_active(older_than=utcnow()):
            entity = api_key_to_domain(api_key)
            entity.expire()
            apply_api_key_domain_to_model(entity, api_key)
            await self.repos.api_keys.update(api_key)
            expired.append(api_key)
        return expired
