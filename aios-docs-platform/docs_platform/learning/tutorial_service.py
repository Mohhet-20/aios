"""Learning Platform: tutorials across the four types the prompt
specifies (getting started, interactive tutorial, hands-on lab,
step-by-step guide), each tagged with the role it targets
(administrator, developer, enterprise customer)."""
from __future__ import annotations

from docs_platform.config.settings import get_settings
from docs_platform.core.exceptions import LearningError, TutorialNotFoundError, UnsupportedTutorialTypeError
from docs_platform.models.learning import TutorialModel
from docs_platform.repositories.registry import RepositoryRegistry


class TutorialService:
    def __init__(self, repos: RepositoryRegistry):
        self.repos = repos
        self.settings = get_settings()

    async def get_or_404(self, tenant_id: str, tutorial_id: str) -> TutorialModel:
        tutorial = await self.repos.tutorials.get_or_404(tutorial_id)
        if tutorial.tenant_id != tenant_id:
            raise TutorialNotFoundError(f"Tutorial '{tutorial_id}' not found for tenant '{tenant_id}'")
        return tutorial

    async def create_tutorial(
        self, tenant_id: str, *, tutorial_type: str, title: str, role: str,
        steps: list[dict] | None = None, pass_threshold_pct: float | None = None,
    ) -> TutorialModel:
        if tutorial_type not in self.settings.tutorial_types:
            raise UnsupportedTutorialTypeError(f"Unsupported tutorial type '{tutorial_type}'")
        if role not in self.settings.learning_roles:
            raise LearningError(f"Unsupported learning role '{role}'")
        tutorial = TutorialModel(
            tenant_id=tenant_id, tutorial_type=tutorial_type, title=title, role=role, steps=steps or [],
            pass_threshold_pct=pass_threshold_pct if pass_threshold_pct is not None else self.settings.tutorial_pass_threshold_pct,
        )
        return await self.repos.tutorials.add(tutorial)

    async def list_tutorials(self, tenant_id: str, *, role: str | None = None, tutorial_type: str | None = None) -> list[TutorialModel]:
        return await self.repos.tutorials.list_for_tenant(tenant_id, role=role, tutorial_type=tutorial_type)
