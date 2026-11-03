"""Plugin packaging: hashes a plugin's file contents into a single
checksum and records it (plus an opaque storage pointer) inside the
version's own manifest under a `package` key — "own the pointer, not
the data" again, without needing a dedicated storage column since the
manifest JSON blob already holds everything else about the version."""
from __future__ import annotations

import hashlib

from developer_platform.core.exceptions import PluginNotFoundError
from developer_platform.models.plugins import PluginVersionModel
from developer_platform.repositories.registry import RepositoryRegistry


def compute_package_checksum(files: dict[str, bytes]) -> str:
    hasher = hashlib.sha256()
    for path in sorted(files):
        hasher.update(path.encode())
        hasher.update(files[path])
    return hasher.hexdigest()


class PluginPackagingService:
    def __init__(self, repos: RepositoryRegistry):
        self.repos = repos

    async def package_version(
        self, tenant_id: str, plugin_version_id: str, *, files: dict[str, bytes], storage_uri: str | None = None,
    ) -> PluginVersionModel:
        record = await self.repos.plugin_versions.get_or_404(plugin_version_id)
        if record.tenant_id != tenant_id:
            raise PluginNotFoundError(f"Plugin version '{plugin_version_id}' not found for tenant '{tenant_id}'")

        entrypoint = record.manifest.get("entrypoint")
        errors = list(record.validation_errors)
        if entrypoint and entrypoint not in files:
            errors.append(f"entrypoint '{entrypoint}' not present in packaged files")

        checksum = compute_package_checksum(files)
        manifest = dict(record.manifest)
        manifest["package"] = {
            "checksum": checksum, "file_count": len(files),
            "storage_uri": storage_uri or f"pkg://{record.plugin_id}/{record.version}/{checksum[:12]}",
        }
        record.manifest = manifest
        record.validation_errors = errors
        return await self.repos.plugin_versions.update(record)
