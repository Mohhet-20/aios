"""Package Registry core: publishing, versioning, and deprecation for
every package type this platform distributes (SDKs, plugins, workflow
templates, prompt templates, agent templates) through one generic
catalog. Reuses the same `dev_registry_packages` /
`dev_registry_package_versions` tables the SDK Platform's package
service writes to for `package_type="sdk"` — this service is the
general-purpose surface covering the other four types plus
deprecation-notice scheduling."""
from __future__ import annotations

import asyncio
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime, timedelta

from developer_platform.config.settings import Settings, get_settings
from developer_platform.core.exceptions import PackageNotFoundError, PackageVersionExistsError, ValidationError
from developer_platform.database.base import utcnow
from developer_platform.domain.enums import PackageType, PackageVersionStatus
from developer_platform.models.registry import RegistryPackageModel, RegistryPackageVersionModel
from developer_platform.registry_platform.mappers import apply_package_version_domain_to_model, package_version_to_domain
from developer_platform.repositories.registry import RepositoryRegistry


@dataclass
class DeprecationResult:
    version: RegistryPackageVersionModel
    recommended_removal_at: datetime


class PackageRegistryService:
    """Both `register_package` (get-or-create keyed on
    `tenant_id:name:package_type`) and `publish_version` (check-then-
    insert keyed on `tenant_id:package_id:version`) are check-then-act
    sequences spanning a read and a write — each guarded with its own
    in-process `asyncio.Lock` per key, the same commit-spanning-lock
    pattern used across every other AIOS platform's own "upsert/insert
    by identity" methods, so two concurrent callers can never both
    observe "nothing exists yet" and both insert a duplicate."""

    _register_locks: dict[str, asyncio.Lock] = defaultdict(asyncio.Lock)
    _publish_locks: dict[str, asyncio.Lock] = defaultdict(asyncio.Lock)

    def __init__(self, repos: RepositoryRegistry, *, settings: Settings | None = None):
        self.repos = repos
        self.settings = settings or get_settings()

    def _assert_valid_type(self, package_type: str) -> None:
        if package_type not in {t.value for t in PackageType}:
            raise ValidationError(f"'{package_type}' is not a recognized package type")

    async def register_package(
        self, tenant_id: str, *, name: str, package_type: str, owner_id: str | None = None, description: str | None = None,
    ) -> RegistryPackageModel:
        self._assert_valid_type(package_type)
        lock_key = f"{tenant_id}:{name}:{package_type}"
        async with self._register_locks[lock_key]:
            existing = await self.repos.registry_packages.get_by_name_type(tenant_id, name, package_type)
            if existing is not None:
                return existing
            package = RegistryPackageModel(
                tenant_id=tenant_id, name=name, package_type=package_type, owner_id=owner_id, description=description,
            )
            package = await self.repos.registry_packages.add(package)
            # Commit while still holding the lock — see
            # `PluginLifecycleService.register_plugin` for why.
            await self.repos.session.commit()
            return package

    async def publish_version(
        self, tenant_id: str, package_id: str, *, version: str, language: str | None = None,
        storage_uri: str | None = None, checksum: str | None = None, dependencies: list | None = None,
    ) -> RegistryPackageVersionModel:
        lock_key = f"{tenant_id}:{package_id}:{version}"
        async with self._publish_locks[lock_key]:
            existing = await self.repos.registry_package_versions.get_by_version(tenant_id, package_id, version)
            if existing is not None:
                raise PackageVersionExistsError(f"version '{version}' already exists for package '{package_id}'")

            record = RegistryPackageVersionModel(
                tenant_id=tenant_id, package_id=package_id, version=version, language=language,
                status=PackageVersionStatus.DRAFT.value, storage_uri=storage_uri, checksum=checksum,
                dependencies=dependencies or [],
            )
            record = await self.repos.registry_package_versions.add(record)

            entity = package_version_to_domain(record)
            entity.publish()
            apply_package_version_domain_to_model(entity, record)
            record = await self.repos.registry_package_versions.update(record)
            # Commit while still holding the lock — see
            # `PluginLifecycleService.register_plugin` for why.
            await self.repos.session.commit()
            return record

    async def deprecate_version(self, tenant_id: str, package_id: str, *, version: str) -> DeprecationResult:
        record = await self._get_version_or_404(tenant_id, package_id, version)
        entity = package_version_to_domain(record)
        entity.deprecate()
        apply_package_version_domain_to_model(entity, record)
        record = await self.repos.registry_package_versions.update(record)
        removal_at = utcnow() + timedelta(days=self.settings.package_registry_deprecation_notice_days)
        return DeprecationResult(version=record, recommended_removal_at=removal_at)

    async def get_version(self, tenant_id: str, package_id: str, version: str) -> RegistryPackageVersionModel:
        return await self._get_version_or_404(tenant_id, package_id, version)

    async def list_versions(self, tenant_id: str, package_id: str) -> list[RegistryPackageVersionModel]:
        return await self.repos.registry_package_versions.list_for_package(tenant_id, package_id)

    async def list_by_type(self, tenant_id: str, package_type: str) -> list[RegistryPackageModel]:
        self._assert_valid_type(package_type)
        return await self.repos.registry_packages.list_by_type(tenant_id, package_type)

    async def _get_version_or_404(self, tenant_id: str, package_id: str, version: str) -> RegistryPackageVersionModel:
        record = await self.repos.registry_package_versions.get_by_version(tenant_id, package_id, version)
        if record is None:
            raise PackageNotFoundError(f"version '{version}' not found for package '{package_id}'")
        return record
