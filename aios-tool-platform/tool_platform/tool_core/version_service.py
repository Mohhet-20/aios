"""ToolVersionService: manages the versioned tool *contract* — input/
output JSON Schema, validation rules, capabilities, configuration, auth
requirement, sensitivity level, and execution defaults (timeout/retry/
backoff). Editing always creates or updates a DRAFT version; a
PUBLISHED version is immutable, so an in-flight `ToolExecution` that
captured `tool_version_id` at start time keeps running against the
exact contract it started with even if a newer version gets published
mid-flight — the same reasoning as the Workflow Engine's
WorkflowVersionService, just without a node/edge graph to manage since
a tool version is a single row, not a graph."""
from __future__ import annotations

from jsonschema.validators import Draft7Validator

from tool_platform.core.exceptions import ValidationError
from tool_platform.models.tool import ToolVersionModel
from tool_platform.repositories.registry import RepositoryRegistry
from tool_platform.tool_core.tool_service import ToolService

_DRAFT_EDITABLE_FIELDS = {
    "capabilities", "input_schema", "output_schema", "validation_rules", "configuration", "auth_requirement",
    "sensitivity_level", "default_timeout_seconds", "default_max_retries", "default_retry_backoff_seconds",
    "connector_key", "change_note",
}


class ToolVersionService:
    def __init__(self, repos: RepositoryRegistry):
        self.repos = repos
        self.tools = ToolService(repos)

    async def get_or_create_draft(self, tool_id: str, *, created_by: str) -> ToolVersionModel:
        """Returns the existing draft version for this tool, or creates a
        new one seeded from the current published version's contract (or
        empty defaults, if this is the tool's first version ever)."""
        draft = await self.repos.tool_versions.get_latest_draft(tool_id)
        if draft is not None:
            return draft

        next_number = await self.repos.tool_versions.get_max_version_number(tool_id) + 1
        seed: dict = {}
        tool = await self.repos.tools.get_or_404(tool_id)
        if tool.current_version_id:
            source = await self.repos.tool_versions.get_or_404(tool.current_version_id)
            seed = {
                "capabilities": list(source.capabilities or []), "input_schema": dict(source.input_schema or {}),
                "output_schema": dict(source.output_schema or {}), "validation_rules": dict(source.validation_rules or {}),
                "configuration": dict(source.configuration or {}), "auth_requirement": dict(source.auth_requirement or {}),
                "sensitivity_level": source.sensitivity_level, "default_timeout_seconds": source.default_timeout_seconds,
                "default_max_retries": source.default_max_retries, "default_retry_backoff_seconds": source.default_retry_backoff_seconds,
                "connector_key": source.connector_key,
            }

        return await self.repos.tool_versions.add(ToolVersionModel(
            tool_id=tool_id, version_number=next_number, status="draft", created_by=created_by, **seed,
        ))

    async def list_versions(self, tool_id: str) -> list[ToolVersionModel]:
        return await self.repos.tool_versions.list_for_tool(tool_id)

    async def get_version(self, version_id: str) -> ToolVersionModel:
        return await self.repos.tool_versions.get_or_404(version_id)

    async def _require_draft(self, version_id: str) -> ToolVersionModel:
        version = await self.repos.tool_versions.get_or_404(version_id)
        if version.status != "draft":
            raise ValidationError(f"tool version '{version_id}' is {version.status}, not draft — cannot edit")
        return version

    async def update_draft(self, version_id: str, **fields) -> ToolVersionModel:
        version = await self._require_draft(version_id)
        unknown = set(fields) - _DRAFT_EDITABLE_FIELDS
        if unknown:
            raise ValidationError(f"cannot update fields: {sorted(unknown)}")
        for key, value in fields.items():
            setattr(version, key, value)
        return await self.repos.tool_versions.update(version)

    # -- publishing --------------------------------------------------------------

    async def publish_version(self, version_id: str, *, activate_tool: bool = True) -> ToolVersionModel:
        version = await self._require_draft(version_id)
        self._validate_schemas(version)

        version.status = "published"
        version = await self.repos.tool_versions.update(version)

        if activate_tool:
            await self.tools.publish(version.tool_id, version.id)

        return version

    def _validate_schemas(self, version: ToolVersionModel) -> None:
        for label, schema in (("input_schema", version.input_schema), ("output_schema", version.output_schema)):
            if not schema:
                continue
            try:
                Draft7Validator.check_schema(schema)
            except Exception as exc:
                raise ValidationError(f"tool version '{version.id}' has an invalid {label}: {exc}") from exc

    async def deprecate_version(self, version_id: str) -> ToolVersionModel:
        version = await self.repos.tool_versions.get_or_404(version_id)
        if version.status != "published":
            raise ValidationError(f"only a published version can be deprecated (status: {version.status})")
        version.status = "deprecated"
        return await self.repos.tool_versions.update(version)
