"""SDK version compatibility matrix: for each supported language, a
set of entries pinning a major SDK version to the range of API
versions it speaks. `check_compatible` is the check a real API
gateway would run on every SDK-originated request (identified via a
`User-Agent`-style client header) to reject calls from an SDK major
version that has fallen outside its compatibility window before it
produces confusing downstream errors."""
from __future__ import annotations

import re

from developer_platform.config.settings import Settings, get_settings
from developer_platform.core.exceptions import SdkVersionIncompatibleError, UnsupportedLanguageError, ValidationError
from developer_platform.models.sdk import SdkCompatibilityEntryModel
from developer_platform.repositories.registry import RepositoryRegistry


def _version_key(version: str) -> tuple[int, ...]:
    """Extracts a comparable numeric key from strings like 'v1', 'v12',
    or '1'. Non-numeric suffixes are ignored — this is a comparison
    helper, not a full semver parser."""
    match = re.search(r"\d+", version)
    return (int(match.group()) if match else 0,)


class SdkCompatibilityService:
    def __init__(self, repos: RepositoryRegistry, *, settings: Settings | None = None):
        self.repos = repos
        self.settings = settings or get_settings()

    def _assert_supported_language(self, language: str) -> None:
        if language not in self.settings.sdk_supported_languages:
            raise UnsupportedLanguageError(f"'{language}' is not a supported SDK language")

    async def register_entry(
        self, tenant_id: str, *, language: str, sdk_major_version: int, min_api_version: str,
        max_api_version: str | None = None, is_supported: bool = True,
    ) -> SdkCompatibilityEntryModel:
        self._assert_supported_language(language)
        existing = await self.repos.sdk_compatibility_entries.get_entry(tenant_id, language, sdk_major_version)
        if existing is not None:
            raise ValidationError(
                f"Compatibility entry for {language} major version {sdk_major_version} already registered"
            )
        entry = SdkCompatibilityEntryModel(
            tenant_id=tenant_id, language=language, sdk_major_version=sdk_major_version,
            min_api_version=min_api_version, max_api_version=max_api_version, is_supported=is_supported,
        )
        return await self.repos.sdk_compatibility_entries.add(entry)

    async def mark_unsupported(self, tenant_id: str, *, language: str, sdk_major_version: int) -> SdkCompatibilityEntryModel:
        entry = await self.repos.sdk_compatibility_entries.get_entry(tenant_id, language, sdk_major_version)
        if entry is None:
            raise ValidationError(f"No compatibility entry for {language} major version {sdk_major_version}")
        entry.is_supported = False
        return await self.repos.sdk_compatibility_entries.update(entry)

    async def check_compatible(self, tenant_id: str, *, language: str, sdk_major_version: int, api_version: str) -> bool:
        self._assert_supported_language(language)
        entry = await self.repos.sdk_compatibility_entries.get_entry(tenant_id, language, sdk_major_version)
        if entry is None or not entry.is_supported:
            raise SdkVersionIncompatibleError(
                f"{language} SDK major version {sdk_major_version} is not a registered/supported combination"
            )
        api_key_val = _version_key(api_version)
        if api_key_val < _version_key(entry.min_api_version):
            raise SdkVersionIncompatibleError(
                f"{language} SDK major version {sdk_major_version} requires API >= {entry.min_api_version}, got {api_version}"
            )
        if entry.max_api_version is not None and api_key_val > _version_key(entry.max_api_version):
            raise SdkVersionIncompatibleError(
                f"{language} SDK major version {sdk_major_version} requires API <= {entry.max_api_version}, got {api_version}"
            )
        return True

    async def list_for_language(self, tenant_id: str, language: str) -> list[SdkCompatibilityEntryModel]:
        self._assert_supported_language(language)
        return await self.repos.sdk_compatibility_entries.list_for_language(tenant_id, language)
