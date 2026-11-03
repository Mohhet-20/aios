"""ORM <-> domain-aggregate bridge for `PackageVersion`. This mirrors
`sdk_platform/mappers.py` exactly — both modules operate on the same
generic `dev_registry_package_versions` table but represent distinct
concerns (SDK-specific publishing vs. the general-purpose registry
covering all five package types), so the small mapper is duplicated
here rather than having this generic module import from a
narrower one."""
from __future__ import annotations

from developer_platform.domain.entities import PackageVersion
from developer_platform.domain.enums import PackageVersionStatus
from developer_platform.models.registry import RegistryPackageVersionModel


def package_version_to_domain(model: RegistryPackageVersionModel) -> PackageVersion:
    return PackageVersion(
        id=model.id, status=PackageVersionStatus(model.status),
        published_at=model.published_at, deprecated_at=model.deprecated_at,
    )


def apply_package_version_domain_to_model(entity: PackageVersion, model: RegistryPackageVersionModel) -> None:
    model.status = entity.status.value
    model.published_at = entity.published_at
    model.deprecated_at = entity.deprecated_at
