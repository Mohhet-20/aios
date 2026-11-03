"""API versioning: a registry of released API versions with a guarded
active -> deprecated -> sunset progression. Deprecating a version
stamps `deprecated_at` and computes the disclosed sunset date from
`api_deprecation_notice_days`; callers targeting a sunset version are
rejected outright rather than silently served."""
from __future__ import annotations

from datetime import timedelta

from developer_platform.config.settings import Settings, get_settings
from developer_platform.core.exceptions import UnsupportedApiVersionError, ValidationError
from developer_platform.database.base import utcnow
from developer_platform.domain.enums import ApiVersionStatus
from developer_platform.models.api_platform import ApiVersionModel
from developer_platform.repositories.registry import RepositoryRegistry


class ApiVersionService:
    def __init__(self, repos: RepositoryRegistry, *, settings: Settings | None = None):
        self.repos = repos
        self.settings = settings or get_settings()

    async def register_version(self, version: str, *, notes: str | None = None) -> ApiVersionModel:
        existing = await self.repos.api_versions.get_by_version(version)
        if existing is not None:
            raise ValidationError(f"API version '{version}' is already registered")
        record = ApiVersionModel(version=version, status=ApiVersionStatus.ACTIVE.value, notes=notes)
        return await self.repos.api_versions.add(record)

    async def deprecate_version(self, version: str) -> ApiVersionModel:
        record = await self._get_or_404(version)
        record.status = ApiVersionStatus.DEPRECATED.value
        record.deprecated_at = utcnow()
        record.sunset_at = utcnow() + timedelta(days=self.settings.api_deprecation_notice_days)
        return await self.repos.api_versions.update(record)

    async def sunset_version(self, version: str) -> ApiVersionModel:
        record = await self._get_or_404(version)
        record.status = ApiVersionStatus.SUNSET.value
        return await self.repos.api_versions.update(record)

    async def assert_usable(self, version: str) -> ApiVersionModel:
        record = await self._get_or_404(version)
        if record.status == ApiVersionStatus.SUNSET.value:
            raise UnsupportedApiVersionError(f"API version '{version}' has been sunset")
        return record

    async def list_versions(self) -> list[ApiVersionModel]:
        return await self.repos.api_versions.list_all()

    async def _get_or_404(self, version: str) -> ApiVersionModel:
        record = await self.repos.api_versions.get_by_version(version)
        if record is None:
            raise UnsupportedApiVersionError(f"API version '{version}' is not registered")
        return record
