"""SDK package registry: each supported language gets one
`RegistryPackageModel` (`package_type="sdk"`, name `aios-sdk-{lang}`),
versioned beneath it through the shared guarded draft -> published ->
deprecated `PackageVersion` lifecycle. This is the SDK-facing slice of
the generic Package Registry catalog (`RegistryPackageModel` /
`RegistryPackageVersionModel`) — the same "generic catalog table,
domain-specific service" split used across every AIOS platform."""
from __future__ import annotations

from developer_platform.config.settings import Settings, get_settings
from developer_platform.core.exceptions import PackageVersionExistsError, UnsupportedLanguageError
from developer_platform.domain.enums import PackageType, PackageVersionStatus
from developer_platform.models.registry import RegistryPackageModel, RegistryPackageVersionModel
from developer_platform.repositories.registry import RepositoryRegistry
from developer_platform.sdk_platform.mappers import apply_package_version_domain_to_model, package_version_to_domain


class SdkPackageService:
    def __init__(self, repos: RepositoryRegistry, *, settings: Settings | None = None):
        self.repos = repos
        self.settings = settings or get_settings()

    def _assert_supported_language(self, language: str) -> None:
        if language not in self.settings.sdk_supported_languages:
            raise UnsupportedLanguageError(f"'{language}' is not a supported SDK language")

    async def _get_or_create_package(self, tenant_id: str, language: str, *, owner_id: str | None) -> RegistryPackageModel:
        name = f"aios-sdk-{language}"
        existing = await self.repos.registry_packages.get_by_name_type(tenant_id, name, PackageType.SDK.value)
        if existing is not None:
            return existing
        package = RegistryPackageModel(
            tenant_id=tenant_id, name=name, package_type=PackageType.SDK.value, owner_id=owner_id,
            description=f"Official AIOS Developer Platform SDK for {language}",
        )
        return await self.repos.registry_packages.add(package)

    async def publish_version(
        self, tenant_id: str, *, language: str, version: str, storage_uri: str | None = None,
        checksum: str | None = None, dependencies: list[str] | None = None, owner_id: str | None = None,
    ) -> RegistryPackageVersionModel:
        self._assert_supported_language(language)
        package = await self._get_or_create_package(tenant_id, language, owner_id=owner_id)

        existing = await self.repos.registry_package_versions.get_by_version(tenant_id, package.id, version)
        if existing is not None:
            raise PackageVersionExistsError(f"{language} SDK version '{version}' is already registered")

        record = RegistryPackageVersionModel(
            tenant_id=tenant_id, package_id=package.id, version=version, language=language,
            status=PackageVersionStatus.DRAFT.value, storage_uri=storage_uri, checksum=checksum,
            dependencies=dependencies or [],
        )
        record = await self.repos.registry_package_versions.add(record)

        entity = package_version_to_domain(record)
        entity.publish()
        apply_package_version_domain_to_model(entity, record)
        return await self.repos.registry_package_versions.update(record)

    async def deprecate_version(self, tenant_id: str, *, language: str, version: str) -> RegistryPackageVersionModel:
        self._assert_supported_language(language)
        package = await self._get_or_create_package(tenant_id, language, owner_id=None)
        record = await self.repos.registry_package_versions.get_by_version(tenant_id, package.id, version)
        if record is None:
            raise PackageVersionExistsError(f"{language} SDK version '{version}' is not registered")

        entity = package_version_to_domain(record)
        entity.deprecate()
        apply_package_version_domain_to_model(entity, record)
        return await self.repos.registry_package_versions.update(record)

    async def list_versions(self, tenant_id: str, language: str) -> list[RegistryPackageVersionModel]:
        self._assert_supported_language(language)
        package = await self._get_or_create_package(tenant_id, language, owner_id=None)
        return await self.repos.registry_package_versions.list_for_package(tenant_id, package.id)
