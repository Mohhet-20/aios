"""Plugin lifecycle: register a plugin, create draft versions, run
manifest validation, sign, publish, and deprecate — the guarded
draft -> validated -> signed -> published -> deprecated state machine
enforced by the `PluginVersion` domain entity. Signing always
produces a real HMAC-SHA256 signature over the canonical manifest;
`plugin_signing_required_for_publish` only controls whether
`publish_version` will auto-sign an unsigned version with a
system-attributed signature or refuse outright."""
from __future__ import annotations

import asyncio
import hashlib
import hmac
import json
from collections import defaultdict

from developer_platform.config.settings import Settings, get_settings
from developer_platform.core.exceptions import PluginAlreadyPublishedError, PluginNotFoundError, PluginSigningRequiredError
from developer_platform.domain.enums import PluginVersionStatus
from developer_platform.models.plugins import PluginModel, PluginVersionModel
from developer_platform.plugin_sdk.manifest import validate_manifest
from developer_platform.plugin_sdk.mappers import apply_plugin_version_domain_to_model, plugin_version_to_domain
from developer_platform.repositories.registry import RepositoryRegistry


def _compute_signature(manifest: dict, secret_key: str) -> str:
    canonical = json.dumps(manifest, sort_keys=True, separators=(",", ":")).encode()
    return hmac.new(secret_key.encode(), canonical, hashlib.sha256).hexdigest()


class PluginLifecycleService:
    """`register_plugin` is a get-or-create keyed on `(tenant_id, name)`
    — guarded with an in-process `asyncio.Lock` per key, the same
    commit-spanning-lock pattern used across every other AIOS
    services's own "upsert by identity" methods (e.g. the
    Infrastructure Platform's `K8sResourceService.apply_resource`),
    since two concurrent callers registering the same plugin name for
    the first time would otherwise both observe no existing row and
    both insert, producing a duplicate."""

    _register_locks: dict[str, asyncio.Lock] = defaultdict(asyncio.Lock)

    def __init__(self, repos: RepositoryRegistry, *, settings: Settings | None = None):
        self.repos = repos
        self.settings = settings or get_settings()

    async def register_plugin(
        self, tenant_id: str, *, name: str, category: str, owner_id: str | None = None,
        description: str | None = None, homepage_url: str | None = None,
    ) -> PluginModel:
        lock_key = f"{tenant_id}:{name}"
        async with self._register_locks[lock_key]:
            existing = await self.repos.plugins.get_by_name(tenant_id, name)
            if existing is not None:
                return existing
            plugin = PluginModel(
                tenant_id=tenant_id, name=name, category=category, owner_id=owner_id,
                description=description, homepage_url=homepage_url,
            )
            plugin = await self.repos.plugins.add(plugin)
            # Commit while still holding the lock — releasing the lock
            # before the row is durably committed would reopen the
            # exact race the lock exists to close, since a waiting
            # caller's `get_by_name` would run against a connection
            # that can't yet see this insert.
            await self.repos.session.commit()
            return plugin

    async def create_version(self, tenant_id: str, plugin_id: str, *, version: str, manifest: dict) -> PluginVersionModel:
        record = PluginVersionModel(
            tenant_id=tenant_id, plugin_id=plugin_id, version=version, manifest=manifest,
            status=PluginVersionStatus.DRAFT.value, validation_errors=[],
        )
        return await self.repos.plugin_versions.add(record)

    async def validate_version(self, tenant_id: str, plugin_version_id: str) -> PluginVersionModel:
        record = await self._get_version_or_404(tenant_id, plugin_version_id)
        errors = validate_manifest(record.manifest)
        record.validation_errors = errors
        if not errors:
            entity = plugin_version_to_domain(record)
            entity.mark_validated()
            apply_plugin_version_domain_to_model(entity, record)
        return await self.repos.plugin_versions.update(record)

    async def invalidate_version(self, tenant_id: str, plugin_version_id: str) -> PluginVersionModel:
        record = await self._get_version_or_404(tenant_id, plugin_version_id)
        entity = plugin_version_to_domain(record)
        entity.invalidate()
        apply_plugin_version_domain_to_model(entity, record)
        return await self.repos.plugin_versions.update(record)

    async def sign_version(self, tenant_id: str, plugin_version_id: str, *, signed_by: str) -> PluginVersionModel:
        record = await self._get_version_or_404(tenant_id, plugin_version_id)
        entity = plugin_version_to_domain(record)
        entity.sign()
        apply_plugin_version_domain_to_model(entity, record)
        record.signature = _compute_signature(record.manifest, self.settings.secret_key)
        record.signed_by = signed_by
        return await self.repos.plugin_versions.update(record)

    async def publish_version(self, tenant_id: str, plugin_version_id: str) -> PluginVersionModel:
        record = await self._get_version_or_404(tenant_id, plugin_version_id)
        if record.status == PluginVersionStatus.PUBLISHED.value:
            raise PluginAlreadyPublishedError(f"Plugin version '{record.id}' is already published")

        if record.status == PluginVersionStatus.VALIDATED.value:
            if self.settings.plugin_signing_required_for_publish:
                raise PluginSigningRequiredError(
                    f"Plugin version '{record.id}' must be signed before it can be published"
                )
            record = await self.sign_version(tenant_id, plugin_version_id, signed_by="system-auto")

        entity = plugin_version_to_domain(record)
        entity.publish()
        apply_plugin_version_domain_to_model(entity, record)
        return await self.repos.plugin_versions.update(record)

    async def deprecate_version(self, tenant_id: str, plugin_version_id: str) -> PluginVersionModel:
        record = await self._get_version_or_404(tenant_id, plugin_version_id)
        entity = plugin_version_to_domain(record)
        entity.deprecate()
        apply_plugin_version_domain_to_model(entity, record)
        return await self.repos.plugin_versions.update(record)

    async def verify_signature(self, tenant_id: str, plugin_version_id: str) -> bool:
        record = await self._get_version_or_404(tenant_id, plugin_version_id)
        if not record.signature:
            return False
        return hmac.compare_digest(record.signature, _compute_signature(record.manifest, self.settings.secret_key))

    async def _get_version_or_404(self, tenant_id: str, plugin_version_id: str) -> PluginVersionModel:
        record = await self.repos.plugin_versions.get_or_404(plugin_version_id)
        if record.tenant_id != tenant_id:
            raise PluginNotFoundError(f"Plugin version '{plugin_version_id}' not found for tenant '{tenant_id}'")
        return record
