"""Package dependency tracking. Unlike the Plugin SDK's dedicated
`dev_plugin_dependencies` table, a package version's dependencies live
directly on `RegistryPackageVersionModel.dependencies` as a JSON list
of `{"name", "package_type", "constraint"}` entries — appropriate here
because packages don't need the richer per-edge metadata plugins do,
just "what else does this pull in." `resolve_dependencies` walks the
graph resolving each named dependency to its latest published version
and detects cycles the same way the Plugin SDK's dependency service
does."""
from __future__ import annotations

from developer_platform.core.exceptions import PackageDeprecatedError, PackageNotFoundError
from developer_platform.domain.enums import PackageVersionStatus
from developer_platform.models.registry import RegistryPackageVersionModel
from developer_platform.repositories.registry import RepositoryRegistry


class PackageDependencyService:
    def __init__(self, repos: RepositoryRegistry):
        self.repos = repos

    async def add_dependency(
        self, tenant_id: str, package_id: str, *, version: str, depends_on_name: str,
        depends_on_type: str, constraint: str = "*",
    ) -> RegistryPackageVersionModel:
        record = await self._get_version_or_404(tenant_id, package_id, version)
        dependencies = list(record.dependencies)
        dependencies.append({"name": depends_on_name, "package_type": depends_on_type, "constraint": constraint})
        record.dependencies = dependencies
        return await self.repos.registry_package_versions.update(record)

    async def resolve_dependencies(self, tenant_id: str, package_id: str, *, version: str) -> list[RegistryPackageVersionModel]:
        resolved: list[RegistryPackageVersionModel] = []
        visiting: set[str] = set()

        async def _walk(pkg_id: str, ver: str) -> None:
            key = f"{pkg_id}:{ver}"
            if key in visiting:
                raise PackageDeprecatedError(f"circular package dependency detected at '{key}'")
            visiting.add(key)

            record = await self._get_version_or_404(tenant_id, pkg_id, ver)
            for dep in record.dependencies:
                target_package = await self.repos.registry_packages.get_by_name_type(
                    tenant_id, dep["name"], dep["package_type"]
                )
                if target_package is None:
                    raise PackageNotFoundError(f"dependency package '{dep['name']}' ({dep['package_type']}) not found")

                target_version = await self._latest_published_version(tenant_id, target_package.id)
                if target_version is None:
                    raise PackageNotFoundError(
                        f"dependency package '{dep['name']}' has no published version to resolve"
                    )
                resolved.append(target_version)
                await _walk(target_package.id, target_version.version)

            visiting.discard(key)

        await _walk(package_id, version)
        return resolved

    async def _get_version_or_404(self, tenant_id: str, package_id: str, version: str) -> RegistryPackageVersionModel:
        record = await self.repos.registry_package_versions.get_by_version(tenant_id, package_id, version)
        if record is None:
            raise PackageNotFoundError(f"version '{version}' not found for package '{package_id}'")
        return record

    async def _latest_published_version(self, tenant_id: str, package_id: str) -> RegistryPackageVersionModel | None:
        versions = await self.repos.registry_package_versions.list_for_package(tenant_id, package_id)
        published = [v for v in versions if v.status == PackageVersionStatus.PUBLISHED.value]
        if not published:
            return None
        return max(published, key=lambda v: v.created_at)
