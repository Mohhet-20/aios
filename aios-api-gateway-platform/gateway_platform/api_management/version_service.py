"""API versioning: a registry of released API versions with a guarded
active -> deprecated -> retired progression. Deprecating a version
computes the disclosed sunset date from `api_deprecation_notice_days`;
callers targeting a retired version are rejected outright rather than
silently served."""
from __future__ import annotations

from datetime import timedelta

from gateway_platform.api_management.mappers import api_version_to_domain, apply_api_version_domain_to_model
from gateway_platform.config.settings import Settings, get_settings
from gateway_platform.core.exceptions import ApiVersionNotFoundError, ApiVersionRetiredError, ValidationError
from gateway_platform.database.base import utcnow
from gateway_platform.domain.enums import ApiVersionStatus
from gateway_platform.models.api_management import ApiVersionModel
from gateway_platform.repositories.registry import RepositoryRegistry


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
        entity = api_version_to_domain(record)
        entity.deprecate(sunset_at=utcnow() + timedelta(days=self.settings.api_deprecation_notice_days))
        apply_api_version_domain_to_model(entity, record)
        return await self.repos.api_versions.update(record)

    async def retire_version(self, version: str) -> ApiVersionModel:
        record = await self._get_or_404(version)
        entity = api_version_to_domain(record)
        entity.retire()
        apply_api_version_domain_to_model(entity, record)
        return await self.repos.api_versions.update(record)

    async def assert_usable(self, version: str) -> ApiVersionModel:
        record = await self._get_or_404(version)
        if record.status == ApiVersionStatus.RETIRED.value:
            raise ApiVersionRetiredError(f"API version '{version}' has been retired")
        return record

    async def list_versions(self) -> list[ApiVersionModel]:
        return await self.repos.api_versions.list_all()

    async def _get_or_404(self, version: str) -> ApiVersionModel:
        record = await self.repos.api_versions.get_by_version(version)
        if record is None:
            raise ApiVersionNotFoundError(f"API version '{version}' is not registered")
        return record
