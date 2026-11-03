"""Learning Platform: ordered learning paths — a named sequence of
tutorial ids targeting one role, giving role-based onboarding
(administrator training, developer training, enterprise customer
onboarding) a single enrollable unit instead of a loose list of
tutorials."""
from __future__ import annotations

from docs_platform.config.settings import get_settings
from docs_platform.core.exceptions import LearningError, LearningPathNotFoundError
from docs_platform.models.learning import LearningPathModel
from docs_platform.repositories.registry import RepositoryRegistry


class LearningPathService:
    def __init__(self, repos: RepositoryRegistry):
        self.repos = repos
        self.settings = get_settings()

    async def get_or_404(self, tenant_id: str, path_id: str) -> LearningPathModel:
        path = await self.repos.learning_paths.get_or_404(path_id)
        if path.tenant_id != tenant_id:
            raise LearningPathNotFoundError(f"Learning path '{path_id}' not found for tenant '{tenant_id}'")
        return path

    async def create_path(self, tenant_id: str, *, name: str, role: str, tutorial_ids: list[str] | None = None) -> LearningPathModel:
        if role not in self.settings.learning_roles:
            raise LearningError(f"Unsupported learning role '{role}'")
        path = LearningPathModel(tenant_id=tenant_id, name=name, role=role, tutorial_ids=tutorial_ids or [])
        return await self.repos.learning_paths.add(path)

    async def list_paths(self, tenant_id: str, *, role: str | None = None) -> list[LearningPathModel]:
        return await self.repos.learning_paths.list_for_tenant(tenant_id, role=role)
