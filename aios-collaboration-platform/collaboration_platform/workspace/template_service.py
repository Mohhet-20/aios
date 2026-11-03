"""WorkspaceTemplateService: reusable workspace starting configs
(settings + default folder/tag layout). A small built-in "blank"
template is idempotently seeded, mirroring the seed-once pattern the
Identity Platform's `seed_builtin_roles` established."""
from __future__ import annotations

from collaboration_platform.models.workspace import WorkspaceTemplateModel
from collaboration_platform.repositories.registry import RepositoryRegistry

BUILTIN_TEMPLATES: list[dict] = [
    {"name": "Blank", "description": "An empty workspace with no preset structure.", "config": {}},
    {
        "name": "Product Team", "description": "Prompt/agent library, roadmap project, and a shared knowledge base folder.",
        "config": {"default_projects": ["Roadmap"], "default_folders": ["Prompts", "Knowledge Base"]},
    },
    {
        "name": "AI Research", "description": "Dataset/model tracking with an experiments project.",
        "config": {"default_projects": ["Experiments"], "default_folders": ["Datasets", "Models"]},
    },
]


class WorkspaceTemplateService:
    def __init__(self, repos: RepositoryRegistry):
        self.repos = repos

    async def seed_builtin_templates(self) -> int:
        existing = await self.repos.workspace_templates.list_builtin()
        existing_names = {t.name for t in existing}
        created = 0
        for spec in BUILTIN_TEMPLATES:
            if spec["name"] in existing_names:
                continue
            await self.repos.workspace_templates.add(
                WorkspaceTemplateModel(name=spec["name"], description=spec["description"], config=spec["config"], is_builtin=True)
            )
            created += 1
        return created

    async def create_custom_template(self, *, name: str, description: str | None = None, config: dict | None = None) -> WorkspaceTemplateModel:
        return await self.repos.workspace_templates.add(
            WorkspaceTemplateModel(name=name, description=description, config=config or {}, is_builtin=False)
        )

    async def list_templates(self) -> list[WorkspaceTemplateModel]:
        return await self.repos.workspace_templates.list(limit=1000)
