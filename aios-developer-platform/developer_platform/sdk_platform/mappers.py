"""ORM <-> domain-aggregate bridge for `PackageVersion`, scoped here
to the SDK Platform's own package-version writes. The Package Registry
module (a later task) may grow a fuller generic service over the same
`dev_registry_package_versions` table; this mapper is safe to reuse or
mirror there since it only touches the guarded-lifecycle fields."""
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
