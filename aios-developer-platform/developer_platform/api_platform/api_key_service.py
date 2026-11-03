"""ApiKeyService: issues scoped, hashed-at-rest API keys. The raw key
is only ever returned once, at issuance/rotation; `key_prefix` (a
non-secret leading slice of the raw key) is what a "your API keys"
list UI shows so an owner can recognize `dpk_a1b2c3d4...` without the
platform ever storing or re-displaying the full secret."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import timedelta

from developer_platform.api_platform.mappers import api_key_to_domain, apply_api_key_domain_to_model
from developer_platform.config.settings import Settings, get_settings
from developer_platform.core.exceptions import ApiKeyExpiredError, ApiKeyRevokedError
from developer_platform.database.base import utcnow
from developer_platform.domain.entities import _aware
from developer_platform.domain.enums import ApiKeyStatus
from developer_platform.models.api_platform import ApiKeyModel
from developer_platform.repositories.registry import RepositoryRegistry
from developer_platform.security.tokens import generate_raw_token, hash_token


@dataclass
class ApiKeyIssueResult:
    api_key: ApiKeyModel
    raw_key: str


class ApiKeyService:
    def __init__(self, repos: RepositoryRegistry, *, settings: Settings | None = None):
        self.repos = repos
        self.settings = settings or get_settings()

    async def issue_key(
        self, tenant_id: str, *, name: str, scopes: list[str] | None = None,
        rate_limit_per_minute: int | None = None, ttl_days: int | None = None,
    ) -> ApiKeyIssueResult:
        expires_at = None
        if ttl_days is not None:
            expires_at = utcnow() + timedelta(days=ttl_days)

        raw_key = f"{self.settings.api_key_prefix}{generate_raw_token()}"
        key_prefix = raw_key[:12]

        api_key = ApiKeyModel(
            tenant_id=tenant_id, name=name, key_hash=hash_token(raw_key), key_prefix=key_prefix,
            scopes=scopes or [], status=ApiKeyStatus.ACTIVE.value,
            rate_limit_per_minute=rate_limit_per_minute or self.settings.api_key_default_rate_limit_per_minute,
            expires_at=expires_at,
        )
        api_key = await self.repos.api_keys.add(api_key)
        return ApiKeyIssueResult(api_key=api_key, raw_key=raw_key)

    async def verify_key(self, raw_key: str) -> ApiKeyModel:
        api_key = await self.repos.api_keys.get_by_key_hash(hash_token(raw_key))
        if api_key is None:
            raise ApiKeyRevokedError("API key is invalid")
        if api_key.status == ApiKeyStatus.REVOKED.value:
            raise ApiKeyRevokedError(f"API key '{api_key.id}' has been revoked")
        if api_key.status == ApiKeyStatus.EXPIRED.value or (
            api_key.expires_at is not None and _aware(api_key.expires_at) < utcnow()
        ):
            if api_key.status != ApiKeyStatus.EXPIRED.value:
                entity = api_key_to_domain(api_key)
                entity.expire()
                apply_api_key_domain_to_model(entity, api_key)
                await self.repos.api_keys.update(api_key)
            raise ApiKeyExpiredError(f"API key '{api_key.id}' has expired")

        api_key.last_used_at = utcnow()
        return await self.repos.api_keys.update(api_key)

    async def revoke_key(self, api_key_id: str) -> ApiKeyModel:
        api_key = await self.repos.api_keys.get_or_404(api_key_id)
        entity = api_key_to_domain(api_key)
        entity.revoke()
        apply_api_key_domain_to_model(entity, api_key)
        return await self.repos.api_keys.update(api_key)

    async def rotate_key(self, api_key_id: str) -> ApiKeyIssueResult:
        """Revokes the old key and issues a fresh one with identical
        scopes/rate limit — the old raw key stops working the instant
        this returns, so a caller must swap to the new one immediately."""
        old = await self.repos.api_keys.get_or_404(api_key_id)
        await self.revoke_key(api_key_id)
        return await self.issue_key(
            old.tenant_id, name=old.name, scopes=list(old.scopes),
            rate_limit_per_minute=old.rate_limit_per_minute,
        )

    async def list_for_tenant(self, tenant_id: str) -> list[ApiKeyModel]:
        return await self.repos.api_keys.list_for_tenant(tenant_id)

    async def sweep_expirations(self, tenant_id: str) -> list[ApiKeyModel]:
        expired: list[ApiKeyModel] = []
        for api_key in await self.repos.api_keys.list_for_tenant(tenant_id):
            if api_key.status != ApiKeyStatus.ACTIVE.value:
                continue
            if api_key.expires_at is not None and _aware(api_key.expires_at) < utcnow():
                entity = api_key_to_domain(api_key)
                entity.expire()
                apply_api_key_domain_to_model(entity, api_key)
                await self.repos.api_keys.update(api_key)
                expired.append(api_key)
        return expired
