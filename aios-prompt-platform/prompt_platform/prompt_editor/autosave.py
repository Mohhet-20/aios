"""Autosave: persists in-progress edits to a DRAFT version without
enforcing validation (a mid-sentence draft is expected to be momentarily
"invalid" — that's fine, autosave's only job is "don't lose the user's
work," not "gate quality"). Optimistic locking still applies so two
browser tabs editing the same draft can't silently clobber each other.
"""
from __future__ import annotations

from prompt_platform.core.exceptions import ConflictError, ValidationError
from prompt_platform.domain.enums import VersionStatus
from prompt_platform.prompt_editor.formatting import format_template
from prompt_platform.repositories.registry import RepositoryRegistry


class AutosaveService:
    def __init__(self, repos: RepositoryRegistry):
        self.repos = repos

    async def save_draft(
        self,
        version_id: str,
        *,
        expected_version: int,
        system_template: str | None = None,
        developer_template: str | None = None,
        user_template: str | None = None,
        variables_schema: list[dict] | None = None,
        parameters: dict | None = None,
    ):
        version = await self.repos.versions.get_or_404(version_id)
        if version.status != VersionStatus.DRAFT.value:
            raise ValidationError(f"only DRAFT versions can be autosaved (version is {version.status})")

        if system_template is not None:
            version.system_template = format_template(system_template)
        if developer_template is not None:
            version.developer_template = format_template(developer_template)
        if user_template is not None:
            version.user_template = format_template(user_template) or ""
        if variables_schema is not None:
            version.variables_schema = variables_schema
        if parameters is not None:
            version.parameters = parameters

        try:
            return await self.repos.versions.update(version, expected_version=expected_version)
        except Exception as exc:
            if "concurrently" in str(exc):
                raise ConflictError(str(exc)) from exc
            raise
