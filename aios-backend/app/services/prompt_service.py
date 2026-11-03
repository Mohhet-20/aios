"""PromptService — the richest example of domain-driven design in this
codebase. ORM rows are mapped into the `Prompt`/`PromptVersion` domain
aggregate (`app.domain.entities.prompt`), all promotion/versioning business
rules run against that in-memory aggregate, and the result is mapped back
to ORM rows for persistence. This round-trip is exactly the "domain layer
enforces invariants, infrastructure layer just stores bytes" separation
Clean Architecture asks for.
"""

from __future__ import annotations

from app.clock import utc_now
from app.core.exceptions import NotFoundError
from app.domain.entities.prompt import Prompt as PromptEntity
from app.domain.entities.prompt import PromptVersion as PromptVersionEntity
from app.domain.events.events import PromptPromoted, PromptVersionCreated
from app.domain.value_objects.enums import PromptStatus
from app.events.bus import EventBus
from app.models.prompt import PromptModel, PromptVersionModel
from app.repositories.prompt_repository import PromptRepository, PromptVersionRepository


def _version_to_domain(m: PromptVersionModel) -> PromptVersionEntity:
    return PromptVersionEntity(
        id=m.id,
        prompt_id=m.prompt_id,
        version=m.version,
        content=m.content,
        status=PromptStatus(m.status),
        author_id=m.author_id,
        created_at=m.created_at,
        eval_score=m.eval_score,
    )


class PromptService:
    def __init__(self, prompts: PromptRepository, versions: PromptVersionRepository, event_bus: EventBus):
        self.prompts = prompts
        self.versions = versions
        self.event_bus = event_bus

    async def _load_aggregate(self, prompt_id: str) -> tuple[PromptModel, PromptEntity]:
        prompt_row = await self.prompts.get_or_404(prompt_id)
        version_rows = await self.versions.list_for_prompt(prompt_id)
        aggregate = PromptEntity(
            id=prompt_row.id,
            workspace_id=prompt_row.workspace_id,
            name=prompt_row.name,
            description=prompt_row.description,
            target_model=prompt_row.target_model,
            tags=[t for t in prompt_row.tags.split(",") if t],
            versions=[_version_to_domain(v) for v in version_rows],
        )
        return prompt_row, aggregate

    async def create_version(self, prompt_id: str, content: str, author_id: str) -> PromptVersionModel:
        _, aggregate = await self._load_aggregate(prompt_id)
        new_version = aggregate.add_version(content, author_id, utc_now())

        row = PromptVersionModel(
            prompt_id=prompt_id,
            version=new_version.version,
            content=new_version.content,
            status=new_version.status.value,
            author_id=author_id,
        )
        row = await self.versions.add(row)
        await self.event_bus.publish(
            PromptVersionCreated(prompt_id=prompt_id, version=row.version, actor_id=author_id)
        )
        return row

    async def promote_version(
        self, prompt_id: str, version_number: int, target_status: str, actor_id: str
    ) -> PromptVersionModel:
        _, aggregate = await self._load_aggregate(prompt_id)
        target = PromptStatus(target_status)

        # Business rules (allowed transitions, eval-score gate, "only one
        # production version") run entirely inside the domain aggregate.
        promoted = aggregate.promote_version(version_number, target)

        # Persist every version whose status the aggregate changed (the
        # promoted one, plus any version it demoted as a side effect).
        for v in aggregate.versions:
            row = await self.versions.get_by_version_number(prompt_id, v.version)
            if row and row.status != v.status.value:
                row.status = v.status.value
                await self.versions.update(row)

        await self.event_bus.publish(
            PromptPromoted(
                prompt_id=prompt_id, version=version_number, to_status=target.value, actor_id=actor_id
            )
        )
        return await self.versions.get_by_version_number(prompt_id, promoted.version)

    async def render(self, prompt_id: str, variables: dict[str, str]) -> str:
        version = await self.versions.get_production_version(prompt_id)
        if version is None:
            version_rows = await self.versions.list_for_prompt(prompt_id)
            version = version_rows[0] if version_rows else None
        if version is None:
            raise NotFoundError(f"Prompt '{prompt_id}' has no versions to render")

        rendered = version.content
        for key, value in variables.items():
            rendered = rendered.replace(f"{{{{{key}}}}}", value)
        return rendered
