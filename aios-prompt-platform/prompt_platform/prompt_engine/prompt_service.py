"""Core Prompt CRUD + dependency-graph management. Version lifecycle
(approval/promotion) lives in versioning_service.py — this service owns
the Prompt's own identity/metadata and its relationships to other prompts.
"""
from __future__ import annotations


from slugify import slugify

from prompt_platform.core.exceptions import ValidationError
from prompt_platform.domain.dependency_graph import validate_no_cycle
from prompt_platform.domain.enums import DependencyRelationship
from prompt_platform.models.prompt import PromptModel
from prompt_platform.models.version import PromptDependencyModel, PromptHistoryModel
from prompt_platform.repositories.registry import RepositoryRegistry
from prompt_platform.clock import utc_now


class PromptService:
    def __init__(self, repos: RepositoryRegistry):
        self.repos = repos

    async def create_prompt(
        self, *, workspace_id: str, project_id: str, name: str, owner_id: str, description: str | None = None, slug: str | None = None
    ) -> PromptModel:
        resolved_slug = slug or slugify(name)
        existing = await self.repos.prompts.get_by_slug(project_id, resolved_slug)
        if existing is not None:
            raise ValidationError(f"a prompt with slug '{resolved_slug}' already exists in this project")

        prompt = await self.repos.prompts.add(
            PromptModel(workspace_id=workspace_id, project_id=project_id, name=name, slug=resolved_slug, description=description, owner_id=owner_id)
        )
        await self._record_history(prompt.id, None, owner_id, "prompt_created", before=None, after={"name": name})
        return prompt

    async def update_metadata(self, prompt_id: str, actor_id: str, **fields) -> PromptModel:
        prompt = await self.repos.prompts.get_or_404(prompt_id)
        before = {k: getattr(prompt, k) for k in fields}
        for key, value in fields.items():
            setattr(prompt, key, value)
        updated = await self.repos.prompts.update(prompt)
        await self._record_history(prompt_id, None, actor_id, "prompt_updated", before=before, after=fields)
        return updated

    async def delete_prompt(self, prompt_id: str, actor_id: str) -> None:
        prompt = await self.repos.prompts.get_or_404(prompt_id)
        await self.repos.prompts.delete(prompt)
        await self._record_history(prompt_id, None, actor_id, "prompt_deleted", before=None, after=None)

    async def add_dependency(self, prompt_id: str, depends_on_prompt_id: str, relationship_type: DependencyRelationship = DependencyRelationship.REFERENCE) -> PromptDependencyModel:
        await self.repos.prompts.get_or_404(prompt_id)
        await self.repos.prompts.get_or_404(depends_on_prompt_id)
        existing_edges = await self.repos.dependencies.all_edges()
        validate_no_cycle(existing_edges, (prompt_id, depends_on_prompt_id))
        return await self.repos.dependencies.add(
            PromptDependencyModel(prompt_id=prompt_id, depends_on_prompt_id=depends_on_prompt_id, relationship_type=relationship_type.value)
        )

    async def list_dependencies(self, prompt_id: str) -> list[PromptDependencyModel]:
        return await self.repos.dependencies.list_for_prompt(prompt_id)

    async def _record_history(self, prompt_id: str, version_id: str | None, actor_id: str, action: str, *, before, after) -> None:
        await self.repos.history.add(
            PromptHistoryModel(
                prompt_id=prompt_id, version_id=version_id, actor_id=actor_id, action=action,
                before=before, after=after, created_at=utc_now(),
            )
        )
